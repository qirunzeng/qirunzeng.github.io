---
title: 'Written Exam Solution of Summer Camp of the Chinese University of Hong Kong 2024'
date: 2024-07-18
permalink: /posts/2024/07/CUHK-SEEM-SummerCamp/
tags:
  - Written Exam
  - Statistics
  - Data Structure
  - Algorithm
  - CUHK
---

- How many distinct ways can 15 people be seated at three round tables with 5 people each if the tables are distinguishable?

> $$
> \frac{15!}{5^3}
> $$
 

- In a game, a fair die with six sides (1-6) is rolled three times. What is the probability that the sum of the results is exactly 10?
<!-- 简单枚举即可，或者计算所有可能的组合再进行排列，略 -->

> Just enumerate

- Design a data structure to maintain a set that supports the following operations in O(1) time: insert, delete, and getRandom. The operations should support inserting a new element, deleting an existing element, and getting a random element from the set of elements. Explain your design and its time complexity.

> Hash Map + Array：
>
> Key: `num`
>
> Value: a list of indices such that `Array[index] = num`
>
> **INSERT**: Just append to the tail of the array, and add to the hash map.
>
> **DELETE**: Map the hash table to a position in the array, then remove that position, fill in the last element to this position, and don't forget to change the mapping of the hash table
>
> **SAMPLE**: Just get a random `index` and `return array[index]`

See the same problem in [leetcode](https://leetcode.cn/problems/insert-delete-getrandom-o1/description/)

- Given a sorted array of n integers, describe an algorithm to find all pairs of elements that sum up to a given target value with linear time complexity. Explain the steps and justify the time complexity.

> It is easily to write such code as follows using hash map to realize the algorithm.

```Python3
def sol2(nums: List[int], tar: int) -> List[List[int]]:
    ump = {}
    ret = []
    for i, num in enumerate(nums):
        if (tar - num) in ump:
            for j in ump[tar - num]:
                ret.append([i, j])
            ump[tar - num].append(i) 
        else:
            ump[tar - num] = [i]
    return ret
```
Time:  `O(n)`

Space: `O(n)`

> But the algorithm above does not ultilize the quality that the array is sorted.
>
> So we use dual pointers to realize such an algorithm.

```Python3
def sol1(nums: List[int], tar: int) -> List[List[int]]:
    i, j = 0, len(nums) - 1
    ret = []
    while i < j:
        if nums[i] + nums[j] == tar:
            ret.append([i, j])
            '''
            Here you should cope with the problem that: 
            there may exist several numbers having the same value
            '''
        elif nums[i] + nums[j] > tar:
            j -= 1
        else:  # nums[i] + nums[j] < tar
            i += 1
    return ret
```
Time: `O(n)`

Space: `O(1)`