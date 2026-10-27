
from mininet.topo import Topo


class MultiPathTopo(Topo):
    def build(self):
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')

        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')

        # Host-to-switch links
        self.addLink(h1, s1)
        self.addLink(s2, h2)

        # Three parallel links between the switches
        self.addLink(s1, s2)
        self.addLink(s1, s2)
        self.addLink(s1, s2)


topos = {
    'multipath': lambda: MultiPathTopo()
}
