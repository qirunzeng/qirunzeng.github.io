# Validate repository data before templates can silently drop invalid references.
require "yaml"
require "json"
require "digest"

module ContentChecks
  ROOT = File.expand_path("..", __dir__)

  def self.check(root = ROOT)
    publications = YAML.load_file(File.join(root, "_data/publications.yml"))
    home = YAML.load_file(File.join(root, "_data/home.yml"))
    papers = %w[conference journal preprints].flat_map { |key| publications[key] || [] }
    ids = papers.map { |paper| paper.fetch("id") }
    errors = []
    errors << "Publication IDs must be nonempty URL-safe strings" unless ids.all? { |id| id.is_a?(String) && id.match?(/\A[a-z0-9]+(?:-[a-z0-9]+)*\z/) }
    errors << "Duplicate publication IDs" unless ids.uniq == ids
    selected = home.fetch("selected_publications")
    errors << "Duplicate selected publication IDs" unless selected.uniq == selected
    references = selected.dup
    home.fetch("research").fetch("interests").each do |interest|
      related = interest.fetch("papers")
      errors << "Research interest #{interest['title']} needs a nonempty, unique papers list" if related.empty? || related.uniq != related
      references.concat(related)
    end
    home.fetch("news").each do |item|
      %w[text home_text].each do |field|
        next if field == "home_text" && !item.key?(field)
        value = item[field]
        unless value.is_a?(String)
          errors << "News #{field} must be a string"
          next
        end
        references.concat(value.scan(/\[paper:([^\]]+)\]/).flatten)
      end
    end
    references.uniq.each { |id| errors << "Unknown publication reference: #{id}" unless ids.include?(id) }
    papers.each do |paper|
      errors << "Missing title or URL for #{paper['id']}" if paper["title"].to_s.empty? || paper["url"].to_s.empty?
      errors << "Unknown venue group for #{paper['id']}" unless publications.fetch("venue_order").include?(paper["venue_group"])
      errors << "No author marked me for #{paper['id']}" unless paper.fetch("authors").any? { |author| author["me"] }
    end
    features = JSON.parse(File.read(File.join(root, "_data/features.json")))
    errors << "scholar_enabled must be a JSON boolean" unless [true, false].include?(features["scholar_enabled"])
    versions = JSON.parse(File.read(File.join(root, "_data/assets.json")))
    { "css" => "assets/css/main.css", "js" => "assets/js/site.js" }.each do |key, path|
      expected = Digest::SHA256.file(File.join(root, path)).hexdigest[0, 16]
      errors << "Stale asset version for #{path}; run python3 scripts/update_assets.py" unless versions[key] == expected
    end
    abort(errors.join("\n")) unless errors.empty?
    puts "Content checks passed: #{papers.length} papers and all references/assets validated."
  end
end

ContentChecks.check if $PROGRAM_NAME == __FILE__
