"use client";

import * as d3 from 'd3';
import type { CSSProperties, SVGAttributes } from 'react';
import { sankey, sankeyDiagram, SankeyGraph } from 'd3-sankey-diagram';
import { useEffect, useState } from 'react';

type IncomeSankeyProps = {
  sankeyJson: SankeyGraph;
  /** Optional map of node id to formatted value label (e.g. USD with negatives in parentheses). Used when the layout does not preserve valueLabel on node __data__. */
  nodeValueLabels?: Record<string, string>;
};

type SankeyLinkRender = {
  id: number;
  pathD: string;
  fill: string;
  title: string;
  textX?: string | null;
  textY?: string | null;
  textDy?: string | null;
  textContent: string;
};

type SankeyNodeRender = {
  id: number;
  transform: string;
  title: string;
  line: {
    x1?: string | null;
    x2?: string | null;
    y1?: string | null;
    y2?: string | null;
    style?: CSSProperties;
  };
  rect: {
    width?: string | null;
    height?: string | null;
    color?: string | null;
  };
  valueText: {
    dy?: string | null;
    textAnchor?: SVGAttributes<SVGTextElement>["textAnchor"];
    transform?: string | null;
    style?: CSSProperties;
    textContent: string;
  };
  titleText: {
    dy?: string | null;
    textAnchor?: SVGAttributes<SVGTextElement>["textAnchor"];
    transform?: string | null;
    style?: CSSProperties;
    textContent: string;
  };
  clickRect: {
    x?: string | null;
    y?: string | null;
    width?: string | null;
    height?: string | null;
    style?: CSSProperties;
  };
};

export default function IncomeSankey({
  sankeyJson,
  nodeValueLabels,
}: IncomeSankeyProps) {
  const [sankeyLinksForReact, setSankeyLinksForReact] = useState<
    SankeyLinkRender[]
  >([]);
  const [sankeyNodesForReact, setSankeyNodesForReact] = useState<
    SankeyNodeRender[]
  >([]);

  const WIDTH_FOR_LABELS = 80;
  const width = 1152; // max-w-6xl corresponds to 1152px
  const height = 800;
  const layout = sankey()
    .nodeWidth(10)
    .extent([
      [WIDTH_FOR_LABELS, 5],
      [width - WIDTH_FOR_LABELS, height - 5],
    ]);

  const colorScale = d3
    .scaleOrdinal<string, string>()
    .domain([
      "research-and-development",
      "selling-general-and-administrative",
      "impairment-of-long-lived-assets",
    ])
    .range(["#FF6B6B", "#4ECDC4", "#45B7D1"]);

  const diagram = sankeyDiagram().linkColor((d) => colorScale(d.type || ""));

  useEffect(() => {
    if (typeof document === "undefined") return;
    const svg2 = d3.select(
      document.createElementNS("http://www.w3.org/2000/svg", "svg")
    );
    svg2.datum(layout(sankeyJson)).call(diagram as any);
    const links = svg2.selectAll("g.link");
    const nodes = svg2.selectAll("g.node");
    setSankeyLinksForReact(getSankeyLinksForReact(links, colorScale));
    setSankeyNodesForReact(getSankeyNodesForReact(nodes, nodeValueLabels));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- layout, diagram, colorScale are stable
  }, [sankeyJson, nodeValueLabels]);

  const parseStyle = (
    styleString?: string | null
  ): CSSProperties | undefined => {
    if (!styleString) return undefined;
    return styleString
      .split(";")
      .map((part) => part.trim())
      .filter(Boolean)
      .reduce((acc, pair) => {
        const [rawKey, rawValue] = pair.split(":").map((s) => s?.trim());
        if (!rawKey || !rawValue) return acc;
        const key = rawKey.replace(/-([a-z])/g, (_match, chr) =>
          chr.toUpperCase()
        );
        (acc as Record<string, string>)[key] = rawValue;
        return acc;
      }, {} as CSSProperties);
  };

  const toTextAnchor = (
    value?: string | null
  ): SVGAttributes<SVGTextElement>["textAnchor"] => {
    const allowed: Array<
      NonNullable<SVGAttributes<SVGTextElement>["textAnchor"]>
    > = ["start", "middle", "end", "inherit"];
    return allowed.includes(value as NonNullable<(typeof allowed)[number]>)
      ? (value as SVGAttributes<SVGTextElement>["textAnchor"])
      : undefined;
  };

  const getSankeyLinksForReact = (
    links: d3.Selection<d3.BaseType, unknown, SVGSVGElement, unknown>,
    scale: d3.ScaleOrdinal<string, string>
  ) => {
    return links.nodes().map((node, index) => {
      const group = node as SVGGElement & { __data__?: { type?: string } };
      const path = group.querySelector("path");
      const title = group.querySelector("title");
      const text = group.querySelector("text");
      const data = group.__data__;
      const fillColor = scale(data?.type || "");

      return {
        id: index,
        pathD: path?.getAttribute("d") ?? "",
        fill: fillColor,
        title: title?.textContent ?? "",
        textX: text?.getAttribute("x"),
        textY: text?.getAttribute("y"),
        textDy: text?.getAttribute("dy"),
        textContent: text?.textContent ?? "",
      };
    });
  };
  const getSankeyNodesForReact = (
    nodes: d3.Selection<d3.BaseType, unknown, SVGSVGElement, unknown>,
    nodeValueLabels?: Record<string, string>
  ) => {
    return nodes.nodes().map((node, index) => {
      const group = node as SVGGElement & {
        __data__?: { color?: string; valueLabel?: string; id?: string };
      };
      const line = group.querySelector("line");
      const rect = group.querySelector("rect.node-body");
      const valueText = group.querySelector("text.node-value");
      const titleText = group.querySelector("text.node-title");
      const clickRect = group.querySelector("rect.node-click-target");
      const data = group.__data__;
      return {
        id: index,
        transform: group.getAttribute("transform") ?? "",
        title: group.querySelector("title")?.textContent ?? "",
        line: {
          x1: line?.getAttribute("x1"),
          x2: line?.getAttribute("x2"),
          y1: line?.getAttribute("y1"),
          y2: line?.getAttribute("y2"),
          style: parseStyle(line?.getAttribute("style")),
        },
        rect: {
          width: rect?.getAttribute("width"),
          height: rect?.getAttribute("height"),
          color: data?.color || "purple",
        },
        valueText: {
          dy: valueText?.getAttribute("dy"),
          textAnchor: toTextAnchor(
            valueText?.getAttribute("text-anchor") ??
              valueText?.getAttribute("textAnchor")
          ),
          transform: valueText?.getAttribute("transform"),
          style: parseStyle(valueText?.getAttribute("style")),
          textContent:
            (nodeValueLabels && data?.id && nodeValueLabels[data.id]) ??
            (data?.valueLabel !== undefined && data?.valueLabel !== ""
              ? data.valueLabel
              : null) ??
            valueText?.textContent ??
            "",
        },
        titleText: {
          dy: titleText?.getAttribute("dy"),
          textAnchor: toTextAnchor(
            titleText?.getAttribute("text-anchor") ??
              titleText?.getAttribute("textAnchor")
          ),
          transform: titleText?.getAttribute("transform"),
          style: parseStyle(titleText?.getAttribute("style")),
          textContent: titleText?.textContent ?? "",
        },
        clickRect: {
          x: clickRect?.getAttribute("x"),
          y: clickRect?.getAttribute("y"),
          width: clickRect?.getAttribute("width"),
          height: clickRect?.getAttribute("height"),
          style: parseStyle(clickRect?.getAttribute("style")),
        },
      };
    });
  };

  // D3 + GSAP combo example
  //   useEffect(() => {
  //     if (!svgRef.current) return;

  //     // const svgElement = svgRef.current;
  //     // const width = svgElement.clientWidth || 800;
  //     // const height = svgElement.clientHeight || 600;

  //     // const layout = sankey().extent([
  //     //   [20, 20],
  //     //   [width - 40, height - 40],
  //     // ]);
  //     // // layout.ordering()

  //     // const colorScale = d3
  //     //   .scaleOrdinal<string, string>()
  //     //   .domain(["x", "y", "z"])
  //     //   .range(["#FF6B6B", "#4ECDC4", "#45B7D1"]);

  //     // const diagram = sankeyDiagram().linkColor((d) => colorScale(d.type || ""));

  //     const svg = d3.select(svgRef.current);
  //     // eslint-disable-next-line @typescript-eslint/no-explicit-any
  //     svg.datum(layout(sankeyJson)).call(diagram as any);

  //     // Debug: log the SVG structure
  //     console.log("SVG paths found:", svg.selectAll("path").size());
  //     console.log("SVG HTML:", svgRef.current?.innerHTML);

  //     // Attach handler to paths
  //     svg
  //       .selectAll("path")
  //       .on("mouseover", function (_event, d) {
  //         const currentStyle = d3.select(this).attr("style");
  //         console.log("Hovered over:", d);
  //         d3.select(this)
  //           .attr("data-original-style", currentStyle)
  //           .attr("style", currentStyle + "; fill: steelblue !important;");
  //       })
  //       .on("mouseout", function () {
  //         const originalStyle = d3.select(this).attr("data-original-style");
  //         d3.select(this).attr("style", originalStyle);
  //       });
  //     // .on("mouseover", function (_event, d) {
  //     //   console.log("Hovered over:", d);
  //     //   d3.select(svgRef.current).selectAll("path").attr("fill", "steelblue");
  //     // });

  //     // const svg = d3.select(svgRef.current);
  //     // svg.selectAll("*").remove();

  //     // const data = [10, 40, 80, 160, 90, 220];

  //     // svg
  //     //   .selectAll("circle")
  //     //   .data(data)
  //     //   .join("circle")
  //     //   .attr("r", (d) => d / 2)
  //     //   .attr("cx", (_d, i) => 60 + i * 90)
  //     //   .attr("cy", 120)
  //     //   .attr("fill", "steelblue")
  //     //   .attr("opacity", 0.7)
  //     //   .call((sel) =>
  //     //     gsap.from(sel.nodes(), {
  //     //       y: -150,
  //     //       stagger: 0.15,
  //     //       duration: 1.4,
  //     //       ease: "back.out(1.7)",
  //     //       delay: 0.6,
  //     //     }),
  //     //   );
  //     // eslint-disable-next-line react-hooks/exhaustive-deps
  //   }, []);

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-6 sm:px-10 lg:px-16 font-sans">
      <div className="max-w-6xl mx-auto">
        {/* SVG container with border and rounded corners */}
        {/* 
        <div className="flex justify-center w-full">
          <svg
            ref={svgRef}
            width="100%"
            height="600"
            className="border border-gray-300 rounded-lg shadow-sm bg-white"
            style={{ display: "block", maxWidth: "100%" }}
          />
        </div> */}

        <div className="flex justify-center w-full">
          <svg
            // ref={svgRef}
            width="100%"
            height="800"
            className="border border-gray-300 rounded-lg shadow-sm bg-white"
            style={{ display: "block", maxWidth: "100%" }}
          >
            <g className="sankey" transform="translate(0,0)">
              <g className="groups"></g>
              <g className="links">
                {sankeyLinksForReact.map((link) => (
                  <g className="link border border-black" key={link.id}>
                    <path d={link.pathD} fill={link.fill}></path>
                    {link.title && <title>{link.title}</title>}
                    <text
                      className="label"
                      dy={link.textDy ?? undefined}
                      x={link.textX ?? undefined}
                      y={link.textY ?? undefined}
                    >
                      {link.textContent}
                    </text>
                  </g>
                ))}
              </g>
              <g className="nodes">
                {sankeyNodesForReact.map((node) => (
                  <g className="node" key={node.id} transform={node.transform}>
                    <title>{node.title}</title>
                    <line
                      x1={node.line.x1 ?? undefined}
                      x2={node.line.x2 ?? undefined}
                      y1={node.line.y1 ?? undefined}
                      y2={node.line.y2 ?? undefined}
                      style={node.line.style}
                    ></line>
                    <rect
                      fill={node.rect.color || "green"}
                      className="node-body"
                      width={node.rect.width ?? undefined}
                      height={node.rect.height ?? undefined}
                    ></rect>
                    <text
                      className="node-value"
                      dy={node.valueText.dy ?? undefined}
                      textAnchor={node.valueText.textAnchor ?? undefined}
                      transform={node.valueText.transform ?? undefined}
                      style={node.valueText.style}
                    >
                      {node.valueText.textContent}
                    </text>
                    <text
                      className="node-title"
                      dy={node.titleText.dy ?? undefined}
                      textAnchor={node.titleText.textAnchor ?? undefined}
                      transform={node.titleText.transform ?? undefined}
                      style={node.titleText.style}
                    >
                      {node.titleText.textContent}
                    </text>
                    <rect
                      className="node-click-target"
                      x={node.clickRect.x ?? undefined}
                      y={node.clickRect.y ?? undefined}
                      width={node.clickRect.width ?? undefined}
                      height={node.clickRect.height ?? undefined}
                      style={node.clickRect.style}
                    ></rect>
                  </g>
                ))}
              </g>
              <g className="slice-titles"></g>
            </g>
            {/* <g className="sankey" transform="translate(0,0)">
              <g className="groups"></g>
              <g className="links">
                {sankeyLinksForReactShadow.map((link) => (
                  <g className="link" key={link.id}>
                    <path d={link.pathD} fill={link.fill}></path>
                    {link.title && <title>{link.title}</title>}
                  <text
                    className="label"
                      dy={link.textDy ?? undefined}
                      x={link.textX ?? undefined}
                      y={link.textY ?? undefined}
                    >
                      {link.textContent}
                    </text>
                  </g>
                ))}
              </g>
              <g className="nodes">
                {sankeyNodesForReactShadow.map((node) => (
                  <g className="node" key={node.id} transform={node.transform}                  >
                    <title>{node.title}</title>
                  <line
                      x1={node.line.x1 ?? undefined}
                      x2={node.line.x2 ?? undefined}
                      y1={node.line.y1 ?? undefined}
                      y2={node.line.y2 ?? undefined}
                      style={node.line.style}
                  ></line>
                  <rect
                    className="node-body"
                      width={node.rect.width ?? undefined}
                      height={node.rect.height ?? undefined}
                  ></rect>
                  <text
                    className="node-value"
                      dy={node.valueText.dy ?? undefined}
                      textAnchor={node.valueText.textAnchor ?? undefined}
                      transform={node.valueText.transform ?? undefined}
                      style={node.valueText.style}
                    >
                      {node.valueText.textContent}
                  </text>
                  <text
                    className="node-title"
                      dy={node.titleText.dy ?? undefined}
                      textAnchor={node.titleText.textAnchor ?? undefined}
                      transform={node.titleText.transform ?? undefined}
                      style={node.titleText.style}
                    >
                      {node.titleText.textContent}
                  </text>
                  <rect
                    className="node-click-target"
                      x={node.clickRect.x ?? undefined}
                      y={node.clickRect.y ?? undefined}
                      width={node.clickRect.width ?? undefined}
                      height={node.clickRect.height ?? undefined}
                      style={node.clickRect.style}
                  ></rect>
                </g>
                ))}
              </g>
              <g className="slice-titles"></g>
            </g> */}
          </svg>
        </div>
      </div>
    </div>
  );
}
