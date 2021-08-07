from recordclass import recordclass
from collections import namedtuple
from collections import defaultdict
import math
import random
import signal 
import sys
import time

Good = namedtuple('Good', ['name'])
QGood = namedtuple('QGood', ['good', 'qty'])

TRADE = 0
TRADEQTY = 0

def seqClosure(a, b):
    def r():
        a()
        b()
    return r
def cantBuyNothing():
    assert False

def marketBuy(markets, good, requested):
    buyClosure = lambda: None
    totalPrice = 0
    totalQty = 0
    while requested > 0:
        bestPrice = float('inf')
        bestQty = 0
        bestClosure = None
        bestMarket = None
        for m in markets:
            price, qty, closure = m.askPrice(good, requested)
            if qty == 0:
                continue
            pricePer = price / qty
            if pricePer < bestPrice:
                bestPrice = pricePer
                bestQty = qty
                bestClosure = closure
                bestMarket = m
        if bestMarket is None:
            break
        else:
            totalPrice += bestPrice * bestQty
            totalQty += bestQty
            requested -= bestQty
            buyClosure = seqClosure(buyClosure, bestClosure)
            
    return (totalPrice, totalQty, buyClosure)

def marketBuyMany(markets, inputs):
    buyClosure = lambda: None
    totalPrice = 0
    for i in inputs:
        price, qty, closure = marketBuy(markets, i.good, i.qty)
        assert qty <= i.qty
        if qty < i.qty:
            return (float('inf'), cantBuyNothing)
        totalPrice += price
        buyClosure = seqClosure(buyClosure, closure)
    return (totalPrice, buyClosure)

class Producer:
    def __init__(self, output, inputs, capital, initialPrice = float('inf'), initialInventory = 0):
        self._output = output
        self._inputs = inputs
        self._price = initialPrice
        self._inventory = initialInventory
        self._maxInventory = 10 * self._output.qty
        self._capital = capital

    def goodsProduced(self):
        if self._inventory > 0:
            return set([self._output.good])
        else:
            return set()

    def askPrice(self, good, qty):
        def buyClosure(qty):
            def r():
                assert self._inventory >= qty
                self._inventory -= qty
                self._capital += self._price * qty
                global TRADE
                global TRADEQTY
                TRADE += self._price * qty
                TRADEQTY += qty
            return r

        if good != self._output.good:
            return (float('inf'), 0, cantBuyNothing)
        if self._inventory >= qty:
            return (qty * self._price, qty, buyClosure(qty))
        else:
            return (self._inventory * self._price, self._inventory, buyClosure(self._inventory))

    def operate(self, markets):
        if self._inventory >= self._maxInventory:
            return

        price, buyClosure = marketBuyMany(markets, self._inputs)
        if price < self._capital:
            self._capital -= price
            buyClosure()
            self._inventory += self._output.qty
            self._price = price

    def report(self):
        reportLine = f'{self._output.qty} {self._output.good} @ ${self._price:.2f} <- '
        for req in self._inputs:
            reportLine += f'{req.qty} {req.good}, '
        print(reportLine)
        print(f'    ${self._capital:0.2f} | {self._inventory}')


PRODUCERS = [
    Producer(QGood(Good('water'), 10), [ QGood(Good('labor'), 1) ], 1000, initialInventory=100, initialPrice=1),
    Producer(QGood(Good('labor'), 1), [ QGood(Good('corn'), 1), QGood(Good('water'), 1) ], 1000, initialInventory=100, initialPrice=1),
    Producer(QGood(Good('corn'), 10), [ QGood(Good('labor'), 1), QGood(Good('water'), 1) ], 1000),
]

GOODS = [ Good(s) for s in [ 'labor', 'water', 'corn', 'wheat', 'apples', 'wood', 'ore', 'house', 'meat', 'spear' ] ]

def make_producer():
    inputGoods = []
    inputGoods.append(QGood(Good('labor'), random.randrange(1,4)))

    goodsProduced = list(set.union(*[ p.goodsProduced() for p in PRODUCERS ]))

    for i in range(random.randrange(0,4)):
        good = random.choice(goodsProduced)
        if any(g.good == good for g in inputGoods):
            continue
        inputGoods.append(QGood(good, random.randrange(1,4)))

    multiplier = random.randrange(1,10)
    return Producer(QGood(random.choice(GOODS), multiplier), inputGoods, 1000)

ADD_PRODUCER = False

def add_producer(sig, frame):
    global ADD_PRODUCER
    if ADD_PRODUCER:
        sys.exit(0)
    ADD_PRODUCER = True
signal.signal(signal.SIGINT, add_producer)

STEP = 0
while True:
    for p in sorted(PRODUCERS, key=lambda _: random.uniform(0,1)):
        p.operate(PRODUCERS)

    if ADD_PRODUCER:
        ADD_PRODUCER = False
        PRODUCERS.append(make_producer())

    if STEP % 1 == 0:
        print()
        print(f'------ STEP {STEP} ------')
        for p in PRODUCERS:
            p.report()

        print(f'GDP: {TRADEQTY} @ ${TRADE:.2f}')
        TRADE = 0
        TRADEQTY = 0
        
        time.sleep(0.4)

    STEP += 1
