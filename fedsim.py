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

PRICE_INERTIA = 0.9
SCALE_INERTIA = 0.5
PRICE_INVENTORY_BASE = 2

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
    def __init__(self, output, inputs, capital, initialPrice = 1, initialInventory = 0):
        self._output = output
        self._inputs = inputs
        self._price = initialPrice
        self._inventory = initialInventory
        self._maxInventory = 30 * self._output.qty
        self._capital = capital
        self._scale = 1

    def goodsProduced(self):
        if self._inventory > 0:
            return set([self._output.good])
        else:
            return set()

    def _priceScale(self):
        return math.pow(PRICE_INVENTORY_BASE, 1 - 2 * self._inventory / self._maxInventory)

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
        else:
            q = min(qty, self._inventory)
            return (self._priceScale() * q * self._price, q, buyClosure(q))

    def operate(self, markets):
        if self._inventory < self._maxInventory:
            for _ in range(round(self._scale)):
                price, buyClosure = marketBuyMany(markets, self._inputs)
                if price < self._capital:
                    self._capital -= price
                    buyClosure()
                    self._inventory += self._output.qty
                    self._price = PRICE_INERTIA * self._price + (1 - PRICE_INERTIA) * (self._priceScale() * self._price)

        dScale = 1 - 2 * self._inventory / self._maxInventory
        self._scale = SCALE_INERTIA * self._scale + (1 - SCALE_INERTIA) * max(1, self._scale + dScale)

    def reset(self):
        pass

    def report(self):
        reportLine = f'{self._output.qty} {self._output.good} @ ${self._priceScale() * self._price:.2f} <- '
        for req in self._inputs:
            reportLine += f'{req.qty} {req.good}, '
        print(reportLine)
        print(f'    ${self._capital:0.2f} | {self._inventory} | scale {round(self._scale)}x')

class LaborUnion:
    def __init__(self, population, inputs, capital, initialPrice):
        self._population = population
        self._unemployment = population
        self._inputs = inputs
        self._price = initialPrice
        self._capital = capital

    def askPrice(self, good, qty):
        def buyClosure(qty):
            def r():
                self._capital += qty * self._price
                self._unemployment -= qty
            return r
        if good != Good('labor') or self._unemployment == 0:
            return float('inf'), 0, cantBuyNothing
        else:
            q = min(qty, self._unemployment)
            return self._price, q, buyClosure(q)

    def goodsProduced(self):
        return set([Good('labor')])

    def reset(self):
        self._unemployment = self._population

    def operate(self, markets):
        totalPrice = 0
        for _ in range(self._population):
            price, buyClosure = marketBuyMany(markets, self._inputs)
            if self._capital >= price:
                self._capital -= price
                totalPrice += price
                buyClosure()
            else:
                print(f'DEATH: can\'t afford ${price:.2f} with ${self._capital:.2f}')
                self._population -= 1

        if self._population > 0:
            scale = max(1, totalPrice * 10 / self._capital)
            self._price = PRICE_INERTIA * self._price + (1 - PRICE_INERTIA) * (scale * totalPrice / max(1, self._population - self._unemployment))
        else:
            self._price = float('inf')

    def report(self):
        print(f'Population: {self._population} ({self._population - self._unemployment} employed) | Savings: ${self._capital:.2f} | Price: ${self._price:.2f}')


PRODUCERS = [
    LaborUnion(10, [ QGood(Good('corn'), 1), QGood(Good('water'), 1) ], capital=1000, initialPrice=1),
    Producer(QGood(Good('water'), 4), [ QGood(Good('labor'), 1) ], capital=1000, initialInventory=50, initialPrice=1),
    Producer(QGood(Good('water'), 4), [ QGood(Good('labor'), 1) ], capital=1000, initialInventory=50, initialPrice=1),
    Producer(QGood(Good('water'), 4), [ QGood(Good('labor'), 1) ], capital=1000, initialInventory=50, initialPrice=1),
    Producer(QGood(Good('corn'), 4), [ QGood(Good('labor'), 1), QGood(Good('water'), 1) ], capital=1000, initialInventory=50, initialPrice=1),
    Producer(QGood(Good('corn'), 4), [ QGood(Good('labor'), 1), QGood(Good('water'), 1) ], capital=1000, initialInventory=50, initialPrice=1),
    Producer(QGood(Good('corn'), 4), [ QGood(Good('labor'), 1), QGood(Good('water'), 1) ], capital=1000, initialInventory=50, initialPrice=1),
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
    if STEP % 1 == 0:
        print()
        print(f'------ STEP {STEP} ------')
        for p in PRODUCERS:
            p.report()

        print(f'GDP: {TRADEQTY} @ ${TRADE:.2f}')
        TRADE = 0
        TRADEQTY = 0
        
        time.sleep(0.4)

    for p in PRODUCERS:
        p.reset()

    for p in sorted(PRODUCERS, key=lambda _: random.uniform(0,1)):
        p.operate(PRODUCERS)

    if ADD_PRODUCER:
        ADD_PRODUCER = False
        PRODUCERS.append(make_producer())

    STEP += 1
