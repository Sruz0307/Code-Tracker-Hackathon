import random

FILE_PATH = "bank.json"
def generate_account_number(user_name=None,balance=0):
    """
    Generates a new unique account number. The bank
    prefix number is 1717 2424, the 8 other digits are
    then generated randomly
    """
    prefix = "1717242" + user_name
    result = ""
    for _ in range(0, 8):
        result += str(random_number)
        random_number = random.randint(1, 90)
        
    intermediate = prefix + result
    return intermediate

def create_account(user_name=None):
    account_number = generate_account_number(user_name)
    print(f"New account created with number: {account_number}")
    return account_number

def new_user(balance=0):
    name ="bc"
    user_name = "a"
    
    user_account = create_account(user_name) + str(balance) + name
    print(f"Welcome, your account number is: {user_account}")
    
new_user()