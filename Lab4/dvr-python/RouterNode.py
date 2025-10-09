#!/usr/bin/env python
import GuiTextArea, RouterPacket, F
from copy import deepcopy

class RouterNode():
    myID = None
    myGUI = None
    sim = None
    costs = None

    # Access simulator variables with:
    # self.sim.POISONREVERSE, self.sim.NUM_NODES, etc.

    # --------------------------------------------------
    def __init__(self, ID, sim, costs):
        self.myID = ID
        self.sim = sim
        self.myGUI = GuiTextArea.GuiTextArea("  Output window for Router #" + str(ID) + "  ")

        self.costs = deepcopy(costs)
        # neighbor detect
        self.neighbors = []
        for i in range(self.sim.NUM_NODES):
            if (i != self.myID and self.costs[i] != 0 and self.costs[i] != self.sim.INFINITY):
                self.neighbors.append(i)
        # initialize the distancetable
        self.distancetable = [[self.sim.INFINITY for _ in range(self.sim.NUM_NODES)] for _ in range(self.sim.NUM_NODES)]
        for i in range(self.sim.NUM_NODES):
            for neighbor in self.neighbors:
                if i == self.myID:
                    self.distancetable[i][neighbor] = 0
                elif i == neighbor:
                    self.distancetable[i][neighbor] = self.costs[i]
                else:
                    self.distancetable[i][neighbor] = self.sim.INFINITY
        # initialize the routingtable
        self.next_hop = [-1] * self.sim.NUM_NODES
        self.routingtable = [self.sim.INFINITY] * self.sim.NUM_NODES
        self.routingtable[self.myID] = 0
        for neighbor in self.neighbors:
            self.routingtable[neighbor] = self.costs[neighbor]
            self.next_hop[neighbor] = neighbor

        self.send_update()

    # --------------------------------------------------
    def recvUpdate(self, pkt):
        sender_sourceid = pkt.sourceid
        sender_cost = pkt.mincost

        updated = False

        for i in range(self.sim.NUM_NODES):
            if i == self.myID:
                self.distancetable[i][i] = 0
                continue
            # count the total distance via neighbor to dest
            if sender_sourceid in self.neighbors:
                new_distance = self.costs[sender_sourceid] + sender_cost[i]
                # if the distance over than infinity, it's not better route, no update with distance table
                if new_distance >= self.sim.INFINITY:
                    new_distance = self.sim.INFINITY
                    updated = False
                if self.distancetable[i][sender_sourceid] != new_distance:
                    self.distancetable[i][sender_sourceid] = new_distance
                    updated = True
                
        if updated:
            print(f"Receive update from: {sender_sourceid}, update distance table: {self.myID}")
            self.updateRoutingTable()
    # --------------------------------------------------
    def updateRoutingTable(self):
        route_changed = False
        for dest in range(self.sim.NUM_NODES):
            if dest == self.myID:
                self.routingtable[dest] = 0
                self.next_hop[dest] = self.myID
                continue

            min_cost = self.sim.INFINITY
            best_hop = -1
            # find shortest cost and record next hop
            for neighbor in self.neighbors:
                cost_via_neighbor = self.distancetable[dest][neighbor]
                if cost_via_neighbor < min_cost:
                    min_cost = cost_via_neighbor
                    best_hop = neighbor
            
            if self.routingtable[dest] != min_cost or (self.next_hop[dest] != best_hop and best_hop != -1):
                self.routingtable[dest] = min_cost
                self.next_hop[dest] = best_hop
                route_changed = True
            
        if route_changed:
            print(f"Router {self.myID} update routing table")
            self.send_update()
            self.printDistanceTable()

    # --------------------------------------------------
    def sendUpdate(self, pkt):
        self.sim.toLayer2(pkt)

    def send_update(self):
        # only send update to neighbors
        for neighbor in self.neighbors:
            modified_cost = self.routingtable.copy()
            # use posion reverse, if self to dest via neighbor, poison neighbor
            if self.sim.POISONREVERSE:
                for dest in range(self.sim.NUM_NODES):
                    if self.next_hop[dest] == neighbor:
                        modified_cost[dest] = self.sim.INFINITY
                        # print(f"Node {self.myID}:Poison reverse to node {neighbor} for dest {dest}")
        
            packet = RouterPacket.RouterPacket(self.myID, neighbor, modified_cost)
            self.sendUpdate(packet)

    # --------------------------------------------------
    def printDistanceTable(self):
        self.myGUI.println("Current table for " + str(self.myID) +
                           "  at time " + str(self.sim.getClocktime()))
        self.myGUI.println("\nDistencetable:")

        row = "  dst   |"
        for dst in range(self.sim.NUM_NODES):
            row += f"{dst:8d}"
        self.myGUI.println(row)
        self.myGUI.println("-"*80)
        
        column = ""
        for nbr in self.neighbors:
            column = "nbr" + f"{nbr:2d}" + "   |"
            for dst in range(self.sim.NUM_NODES):
                column += f"{self.distancetable[dst][nbr]:8d}"
            self.myGUI.println(column)

        self.myGUI.println("\nOur distance vector and routers:")
        row = "  dst   |"
        for dst in range(self.sim.NUM_NODES):
            row += f"{dst:8d}"
        self.myGUI.println(row)
        self.myGUI.println("-"*80)

        row_cost = "  cost  |"
        row_nexthop = "next_hop|"
        for dst in range(self.sim.NUM_NODES):
            row_cost += f"{self.routingtable[dst]:8d}"
            row_nexthop += f"{self.next_hop[dst]:8d}"
        self.myGUI.print(row_cost + "\n")
        self.myGUI.print(row_nexthop + "\n")
        self.myGUI.print("\n")
        self.myGUI.println("="*80)
    # --------------------------------------------------
    def updateLinkCost(self, dest, newcost):
        self.costs[dest] = newcost
        self.distancetable[dest][dest] = newcost

        if self.updateRoutingTable():
            self.send_update()