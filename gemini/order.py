# represents a single order object
# very simple data structure!

class Order(object):
    def __init__(self, price, volume, type=None, pair=None, orderID=None, timestamp=None):
        """
        markets are usually expressed in terms of BASE_ALT where you buy
        and sell units of BASE with ALT.
        price = price (in units alt) of 1 unit of base
        volume = total volume of base desired
        orderID = necessary for tracking & cancelling & ignoring already executed orders when backtesting
        """
        self.p = float(price)
        self.v = float(volume)
        self.type = str(type).upper() if type is not None else None # buy or sell
        self.pair = (pair[0].upper(), pair[1].upper()) if pair is not None else None # market we are trading on
        self.id = str(orderID) if orderID is not None else None
        self.time = timestamp

    def __str__(self):
        return self.type + " " + str(self.v) + self.pair[0] + " at " + str(self.p) + self.pair[1] + ", ID: " + str(self.id)

    def to_dict(self):
        return {'p':self.p,'v':self.v,'type':self.type,'pair':self.pair[0] + '_' + self.pair[1],'id':self.id}