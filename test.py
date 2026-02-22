
def fact( n):
    res = 1
    for i in range(1, n+1):
        res *= i
    return res
def isDigitorialPermutation(n: int) -> bool:
    res = 0
    n1 = n
    while n1:
        temp = n1 % 10
        res += fact(temp)
        n1 = n1 // 10
    if res == n:
        return True
    else: 
        return False

print(isDigitorialPermutation(415))