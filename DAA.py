def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid]< target:
            left = mid + 1
        else:
            right = mid - 1
    return mid
    
arr = [10, 2, 5, 4, 7, 1, 9]
arr.sort()
target = 5 
result = binary_search(arr, target)
print(f"Element found at index: {result}")