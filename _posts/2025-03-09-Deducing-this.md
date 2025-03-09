---
title: 'Deducing this and lambda'
date: 2025-03-09
permalink: /posts/2025/03/Deducing-this/
tags:
  - C++
---

Today I tried to compile a C++ program but failed, which I remember to be correct.

```c++
#include <iostream>

int main() {
    auto fact = [] (this auto &&fact, int n) -> int {
        if (!(n&~1)) return 1;
        return n * fact(n-1);
    };
    std::cout << fact(5) << std::endl;
    return 0;
}
```

Then I looked for the `C++ Standards Support in GCC` and found this item:

| Language Feature | Available in GCC | SD-6 Feature Test |
| :--: | :--: | :--: |
| `Deducing this` | `g++14` | `__cpp_explicit_this_parameter >= 202110L` |

So I checked it:

```
>>> g++ -std=c++23 -dM -E -x c++ /dev/null | grep __cplusplus
#define __cplusplus 202302L
```

`202302L` is newer than `202110L`. But it cannot compile this code.

Then I realized that `g++` in MacOS is redirected to `/usr/bin/g++ <-> /usr/bin/clang`, which is `Apple clang version 16.0.0 (clang-1600.0.26.6)`. i.e. MacOS uses `clang` as default. `Deducing this` requires `clang-19`, which I found no way to download.

Then I used `homebrew` to install `g++-14` and set `alias g++=/opt/homebrew/bin/g++-14` in `~/.zprofile`.

Then this code can be compiled and executed.