from pybreak import pybreak


def heapsort(lst):
    """
    Heapsort from Rosetta Code.
    This function sorts in-place (it mutates the list).
    """
    pybreak.set_trace()
    for start in range((len(lst) - 2) // 2, -1, -1):
        siftdown(lst, start, len(lst) - 1)

    for end in range(len(lst) - 1, 0, -1):
        lst[end], lst[0] = lst[0], lst[end]
        siftdown(lst, 0, end - 1)
    return lst


def siftdown(lst, start, end):
    root = start
    while True:
        child = root * 2 + 1
        if child > end: break
        if child + 1 <= end and lst[child] < lst[child + 1]:
            child += 1
        if lst[root] < lst[child]:
            lst[root], lst[child] = lst[child], lst[root]
            root = child
        else:
            break


def main():
    numbers = [58, 42, 71, 29, 100, 1, 961, 33]
    result = heapsort(numbers)
    print(result)


if __name__ == "__main__":
    main()
