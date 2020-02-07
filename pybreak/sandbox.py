import pdb

from pybreak import pybreak





def merge_sort(m):
    if len(m) <= 1:  # Base case
        return m

    middle = len(m) // 2
    pybreak.set_trace()
    print("ON LINE 15")
    left = m[:middle]
    print("ON LINE 17")
    right = m[middle:]
    print("ON LINE 18")

    left = merge_sort(left)
    right = merge_sort(right)
    return list(merge(left, right))


def merge(left, right):
    result = []
    left_idx, right_idx = 0, 0
    while left_idx < len(left) and right_idx < len(right):
        if left[left_idx] <= right[right_idx]:
            result.append(left[left_idx])
            left_idx += 1
        else:
            result.append(right[right_idx])
            right_idx += 1

    if left_idx < len(left):
        result.extend(left[left_idx:])
    if right_idx < len(right):
        result.extend(right[right_idx:])
    return result


def main():
    numbers = [58, 42, 71, 29, 100, 1, 961, 33]
    result = merge_sort(numbers)
    print(result)


if __name__ == "__main__":
    main()
