from keras.models import Sequential
from keras.layers import LSTM, TimeDistributed, RepeatVector, Dense
import numpy as np
import wandb
from wandb.keras import WandbCallback
import random
from keras.models import load_model


class CharacterTable(object):
    """Given a set of characters:
    + Encode them to a one hot integer representation
    + Decode the one hot integer representation to their character output
    + Decode a vector of probabilities to their character output
    """

    def __init__(self, chars):
        """Initialize character table.
        # Arguments
            chars: Characters that can appear in the input.
        """
        self.chars = sorted(set(chars))
        self.char_indices = dict((c, i) for i, c in enumerate(self.chars))
        self.indices_char = dict((i, c) for i, c in enumerate(self.chars))

    def encode(self, C, num_rows):
        """One hot encode given string C.
        # Arguments
            num_rows: Number of rows in the returned one hot encoding. This is
                used to keep the # of rows for each data the same.
        """
        x = np.zeros((num_rows, len(self.chars)))
        for i, c in enumerate(C):
            x[i, self.char_indices[c]] = 1
        return x

    def decode(self, x, calc_argmax=True):
        if calc_argmax:
            x = x.argmax(axis=-1)
        return ''.join(self.indices_char[x] for x in x)


# Parameters for the model and dataset.
class config:
    def __init__(self, training_size, digits, hidden_size, batch_size):
        self.training_size = training_size
        self.digits = digits
        self.hidden_size = hidden_size
        self.batch_size = batch_size


config.training_size = 200000
config.digits = 5

config.hidden_size = 256
config.batch_size = 256

# Maximum length of input is 'int + int' (e.g., '345+678'). Maximum length of
# int is DIGITS.

maxlen = config.digits + 1 + config.digits

print(maxlen)
# # All the numbers, plus sign and space for padding.
# list of not:
# chars maxlen ctable

chars = '0123456789-+* '

print(len(chars))

things = ['+', '-', '*']

ctable = CharacterTable(chars)


questions = []
expected = []
seen = set()
print('Generating data...')
while len(questions) < config.training_size:
    f = lambda: int(''.join(np.random.choice(list('0123456789'))
                            for i in range(np.random.randint(1, config.digits + 1))))
    a, b = f(), f()
    # Skip any addition questions we've already seen
    # Also skip any such that x+Y == Y+x (hence the sorting).
    key = tuple(sorted((a, b)))
    if key in seen:
        continue
    seen.add(key)
    # Pad the data with spaces such that it is always MAXLEN.
    thing = random.choice(things)
    q = '{}{}{}'.format(a, thing, b)
    query = q + ' ' * (maxlen - len(q))
    if thing == '-':
        ans = str(a - b)
    elif thing == '+':
        ans = str(a + b)
    elif thing == '*':
        ans = str(a * b)


    # Answers can be of maximum size DIGITS + 1.
    ans += ' ' * (config.digits + 7 - len(ans))
    questions.append(query)
    expected.append(ans)

print('Total addition questions:', len(questions))

print('Vectorization...')
x = np.zeros((len(questions), maxlen, len(chars)), dtype=np.bool)
y = np.zeros((len(questions), config.digits + 7, len(chars)), dtype=np.bool)
for i, sentence in enumerate(questions):
    x[i] = ctable.encode(sentence, maxlen)
for i, sentence in enumerate(expected):
    y[i] = ctable.encode(sentence, config.digits + 7)


# Shuffle (x, y) in unison as the later parts of x will almost all be larger
# digits.
indices = np.arange(len(y))
np.random.shuffle(indices)
x = x[indices]
y = y[indices]

# Explicitly set apart 10% for validation data that we never train over.
split_at = len(x) - len(x) // 10
(x_train, x_val) = x[:split_at], x[split_at:]
(y_train, y_val) = y[:split_at], y[split_at:]

model = Sequential()
model.add(LSTM(config.hidden_size, input_shape=(maxlen, len(chars))))
model.add(RepeatVector(config.digits + 7))
model.add(LSTM(config.hidden_size, return_sequences=True))

model.add(TimeDistributed(Dense(len(chars), activation='softmax')))
model.compile(loss='categorical_crossentropy',
              optimizer='adam',
              metrics=['accuracy'])
model.summary()

# Train the model each generation and show predictions against the validation
# dataset.
for iteration in range(1, 200):
    print('-' * 50)
    print('Iteration', iteration)
    model.fit(x_train, y_train,
              batch_size=config.batch_size,
              epochs=1,
              validation_data=(x_val, y_val))
    model.save('math_model')
    # Select 10 samples from the validation set at random so we can visualize
    # errors.
    for i in range(10):
        ind = np.random.randint(0, len(x_val))
        rowx, rowy = x_val[np.array([ind])], y_val[np.array([ind])]
        preds = model.predict_classes(rowx, verbose=0)
        q = ctable.decode(rowx[0])
        correct = ctable.decode(rowy[0])
        guess = ctable.decode(preds[0], calc_argmax=False)
        print('Q', q, end=' ')
        print('T', correct, end=' ')
        if correct == guess:
            print('☑', end=' ')
        else:
            print('☒', end=' ')
        print(guess)




# while True:
#     question = []
#     query = input('enter: ')
#     q = query + ' ' * (maxlen - len(query))
#     question.append(q)
#
#     test1 = np.zeros((len(question), maxlen, len(chars)), dtype=np.bool)
#     for i, sentence in enumerate(question):
#         test1[i] = ctable.encode(sentence, maxlen)
#     model1 = load_model('math_model')
#     ind = np.random.randint(0, len(test1))
#     xrow1 = test1[np.array([ind])]
#     preds = model1.predict_classes(xrow1)
#     guess = ctable.decode(preds[0], calc_argmax=False)
#     print(guess)


