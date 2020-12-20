import functools

class Movies:
    '''
    电影信息, 包含标题和评分数据, 期望自定义根据评分排序
    '''
    def __init__(self, title='default', score=-0.0): # 初始化操作, 设置默认值
        self.title = title
        self.score = score

    def __str__(self): # 自定义打印类的内容
        return "{} : {}".format(self.title, self.score)

def cmp(self, other): # 自定义比较函数
    if self.score < other.score:
        return -1
    elif self.score == other.score:
        return 0
    else:
        return 1

movie = [0]*3

movie[0] = Movies("电影1", 8.1)

# movie_2 = Movies()
movie[1] = Movies('电影2', 9.2)

movie[2] = Movies("电影3", 3.4)

sorted_movie = sorted(movie, key=functools.cmp_to_key(cmp))
# sorted_movie = sorted(movie, key=lambda mov: -mov.score)

for each in sorted_movie:
    print(each)
