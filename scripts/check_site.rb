# Build and inspect both Scholar states without changing tracked configuration.
require "jekyll"
require "tmpdir"
require_relative "check_content"

ContentChecks.check
root = ContentChecks::ROOT
Dir.chdir(root) do
  Dir.mktmpdir("qirun-site-check-") do |directory|
    paper_ids = nil
    [true, false].each do |enabled|
      destination = File.join(directory, enabled ? "enabled" : "disabled")
      site = Jekyll::Site.new(Jekyll.configuration("source" => root, "destination" => destination, "quiet" => true))
      site.reset
      site.read
      site.data.fetch("features")["scholar_enabled"] = enabled
      site.generate
      site.render
      site.cleanup
      site.write
      unless system("python3", File.join(root, "scripts/check_rendered_site.py"), destination, "--scholar", enabled.to_s)
        abort "Rendered site checks failed"
      end
      current_ids = Dir.glob(File.join(destination, "**/*.html")).sort.map do |path|
        [path.delete_prefix(destination), File.read(path).scan(/id="paper-([^"]+)"/).flatten]
      end
      abort "Scholar switch changed the publication lists" if paper_ids && paper_ids != current_ids
      paper_ids = current_ids
    end
  end
end
puts "Both Scholar states build correctly; publication lists are unchanged."
