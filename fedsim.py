from recordclass import recordclass
from collections import namedtuple

Good = namedtuple('Good', ['name'])

Ask = recordclass('Ask', ['price', 'qty', 'asker'])
Bid = recordclass('Ask', ['price', 'qty', 'bidder'])

class Market:
    def __init__(self, good):
        self.good = good
        self.asks = []
        self.bids = []

    def ask(self, price, qty, asker):
        for i in range(len(self.asks)):
            if price <= self.asks[i].price:
                self.asks.insert(i, Ask(price, qty, asker))
                break
        else:
            self.asks.append(Ask(price, qty, asker))

    def bid(self, price, qty, bidder):
        for i in range(len(self.bids)):
            if price >= self.bids[i].price:
                self.bids.insert(i, Bid(price, qty, bidder))
        else:
            self.bids.append(Bid(price, qty, bidder))

    def balance(self):
        while self.asks and self.bids and self.bids[0].price >= self.asks[0].price:
            qty = min(self.bids[0].qty, self.asks[0].qty)
            price = (self.bids[0].price + self.asks[0].price) / 2
            self.bids[0].qty -= qty
            self.asks[0].qty -= qty

            self.bids[0].bidder.bought(self.good, qty, price)
            self.asks[0].asker.sold(self.good, qty, price)

            if self.bids[0].qty == 0:
                self.bids.pop(0)
            if self.asks[0].qty == 0:
                self.asks.pop(0)

class Logger:
    def __init__(self, name):
        self.name = name

    def bought(self, good, qty, price):
        print(f'{self.name} bought {qty} of {good} at ${price:.2f}')

    def sold(self, good, qty, price):
        print(f'{self.name} sold {qty} of {good} at ${price:.2f}')

market = Market(Good('Coffee'))
market.ask(3.50, 100, Logger('Starbucks'))
market.ask(2.00, 200, Logger('Cheapo'))
market.ask(7.50, 12, Logger('Bougie'))

market.bid(2.50, 1000, Logger('Working Class'))
market.bid(10.0, 100, Logger('Connisseurs'))

market.balance()

Production = namedtuple('Production', ['good', 'goodsRequired'])

