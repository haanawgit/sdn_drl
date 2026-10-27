from mininet.topo import Topo

class AdaptiveTopo(Topo):
    def build(self):
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')

        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')

        self.addLink(h1, s1)

        # Three alternative paths between the switches
        self.addLink(s1, s2)
        self.addLink(s1, s2)
        self.addLink(s1, s2)

        self.addLink(s2, h2)

topos = {'adaptive': lambda: AdaptiveTopo()}
