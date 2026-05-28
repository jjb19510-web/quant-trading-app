class Todolist:
    def __init__(self,todos):
        self.todos = []
    def add(self,todo):
        self.todos.append(todo)
        print(self.todos,'추가됨!')
    def done(self,todo):
        self.todos.remove(todo)
        print(self.todos,'완료!')
    def show(self):
        print('남은 할 일:',self.todos)
t = Todolist()
t.add('공부하기')
t.add('운동하기')
t.add('밥 먹기')
t.done('운동하기')
t.show()
    

        


        
