from pybreak import pybreak


def main():
    pybreak.set_trace()
    numbers = [1]
    numbers.append(2)
    numbers.append(3)
    numbers.append(4)
    numbers.append(5)


if __name__ == "__main__":
    main()
