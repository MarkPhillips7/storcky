declare module "d3-sankey-diagram" {
    export interface SankeyNode {
      id: string;
      title?: string;
      x?: number;
      y?: number;
      dx?: number;
      dy?: number;
      direction?: string;
      color?: string;
      // Add other properties as needed
    }
  
    export interface SankeyLink {
      source: SankeyNode | string;
      target: SankeyNode | string;
      value: number;
      type?: string;
      color?: string;
      // Add other properties as needed
    }
  
    export interface SankeyGraph {
      nodes: SankeyNode[];
      links: SankeyLink[];
      order?: any;
    }
  
    export interface SankeyLayout {
      (data: any): SankeyGraph;
      extent(extent: [[number, number], [number, number]]): this;
      nodeWidth(width: number): this;
      size(size: [number, number]): this;
      nodes(accessor?: (d: any) => any): this | ((d: any) => any);
      links(accessor?: (d: any) => any): this | ((d: any) => any);
      nodeId(accessor?: (d: any) => string): this | ((d: any) => string);
      linkValue(accessor?: (d: any) => number): this | ((d: any) => number);
      ordering(ordering?: any): this | any;
      // Add more methods as needed
    }
  
    export interface SankeyDiagram {
      (selection: d3.Selection<SVGSVGElement, any, any, any>): void;
      linkColor(
        accessor?: (d: SankeyLink) => string | null,
      ): this | ((d: SankeyLink) => string | null);
      // Add more methods as needed
    }
  
    export function sankey(): SankeyLayout;
    export function sankeyDiagram(): SankeyDiagram;
  }
  