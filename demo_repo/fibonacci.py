def fibonacci(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n-1) + fibonacci(n-2)

if __name__ == "__main__":
    n = 10  # Example input
    print(f"Fibonacci sequence up to {n}:")
    for i in range(n+1):
        print(fibonacci(i))