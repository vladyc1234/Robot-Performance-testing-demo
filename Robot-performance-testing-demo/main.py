def count_up_to(limit):
    """Yield numbers from 1 through limit, one at a time."""
    number = 1
    while number <= limit:
        yield number  # Pause here; resume on the next iteration.
        number += 1


if __name__ == "__main__":
    for number in count_up_to(10000000000000000000000):
        print(number)
