import hashlib
import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict

class SDNController:
    def __init__(self):
        # Network topology representation
        self.topology = nx.Graph()
        self.flow_tables = defaultdict(dict)  # {switch_id: {flow: action}}
        self.active_flows = []
        self.link_utilization = defaultdict(int)
        
        # Cryptographic watermark (SHA-256: 298951c47751f04a4c8352d1e3f139eae171c9d298fa12ff9dc60454c72bb5a8)
        student_id = "1727"  # Last 4 digits of university ID
        watermark_text = student_id + "NeoDDaBRgX5a9"
        self.watermark = hashlib.sha256(watermark_text.encode()).hexdigest()
        
    def add_node(self, node_id, node_type='switch'):
        """Add a node to the topology"""
        self.topology.add_node(node_id, type=node_type)
        
    def add_link(self, node1, node2, bandwidth=100):
        """Add a link between two nodes"""
        self.topology.add_edge(node1, node2, bandwidth=bandwidth, 
                             utilization=0, available=True)
    
    def remove_link(self, node1, node2):
        """Mark a link as failed"""
        if self.topology.has_edge(node1, node2):
            self.topology[node1][node2]['available'] = False
    
    def restore_link(self, node1, node2):
        """Restore a failed link"""
        if self.topology.has_edge(node1, node2):
            self.topology[node1][node2]['available'] = True
    
    def compute_paths(self, src, dst, priority=0):
        """
        Compute paths considering link availability and traffic priority
        Implements load balancing and priority routing
        """
        # Get all available links
        available_edges = [(u, v) for u, v, d in self.topology.edges(data=True) 
                         if d['available']]
        subgraph = self.topology.edge_subgraph(available_edges)
        
        try:
            # Find all possible paths
            all_paths = list(nx.all_shortest_paths(subgraph, src, dst))
            
            # Priority routing - select least utilized path for high priority
            if priority > 0:
                return [min(all_paths, key=lambda p: self._path_utilization(p))]
            
            # Load balancing - distribute across multiple paths
            return all_paths[:2]  # Return up to 2 paths for balancing
            
        except nx.NetworkXNoPath:
            return []
    
    def _path_utilization(self, path):
        """Calculate total utilization along a path"""
        total = 0
        for i in range(len(path)-1):
            u, v = path[i], path[i+1]
            total += self.topology[u][v]['utilization']
        return total
    
    def install_flow(self, switch_id, flow, action):
        """Install flow rule on a switch"""
        self.flow_tables[switch_id][flow] = action
    
    def inject_flow(self, src, dst, priority=0, bandwidth=10):
        """
        Inject a traffic flow into the network
        Implements backup paths for critical flows
        """
        # Find primary path
        paths = self.compute_paths(src, dst, priority)
        if not paths:
            print("No available path!")
            return
            
        primary_path = paths[0]
        
        # For critical flows (priority > 1), find a backup path
        backup_path = None
        if priority > 1 and len(paths) > 1:
            backup_path = paths[1]
        
        # Update link utilization
        for i in range(len(primary_path)-1):
            u, v = primary_path[i], primary_path[i+1]
            self.topology[u][v]['utilization'] += bandwidth
        
        # Install flow rules on switches
        flow_id = f"{src}-{dst}-{len(self.active_flows)}"
        for switch in primary_path[1:-1]:  # Skip endpoints
            self.install_flow(switch, flow_id, {"action": "forward", "path": primary_path})
        
        if backup_path:
            for switch in backup_path[1:-1]:
                self.install_flow(switch, flow_id, {"action": "forward", "path": backup_path})
        
        self.active_flows.append({
            "id": flow_id,
            "src": src,
            "dst": dst,
            "primary_path": primary_path,
            "backup_path": backup_path,
            "bandwidth": bandwidth,
            "priority": priority
        })
        
        return flow_id
    
    def visualize(self):
        """Visualize network topology and flows"""
        plt.figure(figsize=(10, 8))
        
        # Draw topology
        pos = nx.spring_layout(self.topology)
        nx.draw_networkx_nodes(self.topology, pos, node_size=500)
        nx.draw_networkx_labels(self.topology, pos)
        
        # Draw available links
        available_edges = [(u, v) for u, v, d in self.topology.edges(data=True) 
                         if d['available']]
        nx.draw_networkx_edges(self.topology, pos, edgelist=available_edges, 
                             width=2, edge_color='b')
        
        # Draw failed links
        failed_edges = [(u, v) for u, v, d in self.topology.edges(data=True) 
                       if not d['available']]
        nx.draw_networkx_edges(self.topology, pos, edgelist=failed_edges, 
                             width=2, edge_color='r', style='dashed')
        
        # Draw active flows
        for flow in self.active_flows:
            path = flow['primary_path']
            path_edges = [(path[i], path[i+1]) for i in range(len(path)-1)]
            nx.draw_networkx_edges(self.topology, pos, edgelist=path_edges, 
                                 width=2, edge_color='g', alpha=0.3)
        
        plt.title("SDN Network Topology and Active Flows")
        plt.show()
        
        # Display utilization statistics
        print("\nLink Utilization Statistics:")
        for u, v, d in self.topology.edges(data=True):
            print(f"Link {u}-{v}: {d['utilization']}/{d['bandwidth']} ({d['utilization']/d['bandwidth']:.1%})")
    
    def cli(self):
        """Simple command-line interface"""
        print(f"SDN Controller (Watermark: {self.watermark})")
        while True:
            print("\nOptions:")
            print("1. Add a node")
            print("2. Add a link")
            print("3. Remove/fail a link")
            print("4. Restore a link")
            print("5. Inject flow")
            print("6. Visualize Topology")
            print("7. Exit")
            
            choice = input("Select option: ")
            
            if choice == '1':
                node_id = input("Enter node ID: ")
                self.add_node(node_id)
                
            elif choice == '2':
                node1 = input("Enter first node: ")
                node2 = input("Enter second node: ")
                bw = int(input("Enter bandwidth (default 100): ") or "100")
                self.add_link(node1, node2, bw)
                
            elif choice == '3':
                node1 = input("Enter first node: ")
                node2 = input("Enter second node: ")
                self.remove_link(node1, node2)
                
            elif choice == '4':
                node1 = input("Enter first node: ")
                node2 = input("Enter second node: ")
                self.restore_link(node1, node2)
                
            elif choice == '5':
                src = input("Enter source node: ")
                dst = input("Enter destination node: ")
                priority = int(input("Enter priority (0=normal, 1=high, 2=critical): "))
                bw = int(input("Enter bandwidth required: "))
                self.inject_flow(src, dst, priority, bw)
                
            elif choice == '6':
                self.visualize()
                
            elif choice == '7':
                break
                
            else:
                print("Invalid option!")

if __name__ == "__main__":
    controller = SDNController()
    
    # Example topology
    controller.add_node('s1')
    controller.add_node('s2')
    controller.add_node('s3')
    controller.add_node('s4')
    controller.add_node('h1')
    controller.add_node('h2')
    
    controller.add_link('s1', 's2')
    controller.add_link('s1', 's3')
    controller.add_link('s2', 's4')
    controller.add_link('s3', 's4')
    controller.add_link('h1', 's1')
    controller.add_link('h2', 's4')
    
    controller.cli()