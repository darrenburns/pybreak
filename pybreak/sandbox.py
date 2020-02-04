from pybreak import pybreak


def main():
    print(1 + 2)
    x = 4
    print("hello world")
    pybreak.set_trace()
    print(x)
    y = "abc"
    pybreak.set_trace()
    z = [1, 2, 3, 4, 5]
    print(y, z)


if __name__ == '__main__':
    main()
