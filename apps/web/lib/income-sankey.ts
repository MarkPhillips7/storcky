import { CompanyFactsResponse, FactPeriod } from './api';
import { SankeyGraph, SankeyLink, SankeyNode } from 'd3-sankey-diagram';

type IncomeSankeyNode = {
  /** Unique income sankey node id. */
  id: string;
  /** Visual order of the node in the graph. Lower numbers are closer to the top of the graph with respect to nodes at the same level.
   */
  order: number;
  /** Optional title for the node. If not provided, will use title from company fact concept identified by tags.*/
  title?: string;
  /** Optional title for the node when the value is negative. If not provided, will use node title or concept label from company fact concept identified by tags. */
  titleWhenNegative?: string;
  /** Optional color for the node. */
  color?: string;
  /** Optional color for the node when the value is negative. */
  colorWhenNegative?: string;
  /** Optional icon for the node. */
  icon?: string;
  /** Optional icon for the node when the value is negative. */
  iconWhenNegative?: string;
  /** Concept tags identifying which company facts to extract values from.
   * If not provided or with no value, the node will not be included in the graph.
   * If provided with a value, the node will be included in the graph and the value will be extracted from the CompanyFact data.
   * If the node has multiple tags, the value will be the sum of the values extracted from the CompanyFact data.
   * If a tag has an action, the value will be altered appropriately (added or subtracted). */
  conceptTags: IncomeSankeyNodeTag[];
  tags?: string[];
  /** Whether to use the prior period value for the node. */
  usePriorPeriod?: boolean;
};

type IncomeSankeyNodeTag =
  | string
  | {
      tag: string;
      action?: "add" | "subtract";
    };

type IncomeSankeyLink = {
  /** Source income sankey node id. */
  source: string;
  /** Target income sankey node id. */
  target: string;
  /** Order in which amounts flow from sources to targets. For example if revenue and bank-account are both sources for cost-of-goods-sold,
   * the order of `revenue => cost-of-goods-sold` should be less than the order of `bank-account => cost-of-goods-sold` for revenue to be
   * the primary source. That way bank-account will only be a source if revenue is less than cost-of-goods-sold.
   */
  order: number;
};

type IncomeSankeyTemplate = {
  nodes: IncomeSankeyNode[];
  links: IncomeSankeyLink[];
};

const defaultIncomeSankeyTemplate: IncomeSankeyTemplate = {
  nodes: [
    {
      id: "revenue",
      order: 1,
      title: "Revenue",
      color: "blue",
      conceptTags: [
        "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
      ],
    },
    {
      id: "bank-account",
      order: 2,
      title: "Bank Account",
      color: "grey",
      conceptTags: ["us-gaap:CashAndCashEquivalentsAtCarryingValue"],
      usePriorPeriod: true,
    },
    {
      id: "gross-profit",
      order: 3,
      title: "Gross Profit",
      titleWhenNegative: "Gross Loss",
      color: "green",
      colorWhenNegative: "red",
      conceptTags: ["us-gaap:GrossProfit"],
    },
    {
      id: "cost-of-goods-sold",
      order: 4,
      title: "Cost of Goods Sold",
      color: "red",
      conceptTags: ["us-gaap:CostOfGoodsAndServicesSold"],
    },
    // Depreciation and Amortization Only Show up in cash flows
    //   {
    //     id: "depreciation-and-amortization",
    //     title: "Depreciation and Amortization",
    //     color: "green",
    //     tag: "us-gaap:DepreciationAndAmortization",
    //   },
    {
      id: "operating-profit",
      order: 5,
      title: "Operating Profit",
      titleWhenNegative: "Operating Loss",
      color: "green",
      colorWhenNegative: "red",
      conceptTags: ["us-gaap:OperatingIncomeLoss"],
      tags: ["EBIT"],
    },
    {
      id: "net-profit",
      order: 6,
      title: "Net Profit",
      titleWhenNegative: "Net Loss",
      color: "green",
      colorWhenNegative: "red",
      conceptTags: ["us-gaap:NetIncomeLoss"],
      tags: ["EAT"],
    },
    {
      id: "operating-expenses",
      order: 7,
      title: "Operating Expenses",
      color: "red",
      conceptTags: ["us-gaap:CostsAndExpenses"],
    },
    {
      id: "research-and-development",
      order: 8,
      title: "Research and Development",
      color: "red",
      conceptTags: ["us-gaap:ResearchAndDevelopmentExpense"],
    },
    {
      id: "selling-general-and-administrative",
      order: 9,
      title: "Selling, General and Administrative",
      color: "red",
      conceptTags: ["us-gaap:SellingGeneralAndAdministrativeExpense"],
    },
    {
      id: "impairment-of-long-lived-assets",
      order: 10,
      title: "Other Expenses",
      color: "red",
      conceptTags: ["us-gaap:ImpairmentOfLongLivedAssetsHeldForUse"],
    },
    {
      id: "interest",
      order: 11,
      title: "Interest",
      color: "red",
      conceptTags: [
        "us-gaap:InterestExpenseNonoperating",
        { tag: "us-gaap:InvestmentIncomeInterest", action: "subtract" },
      ],
    },
    {
      id: "tax",
      order: 12,
      title: "Tax",
      color: "red",
      conceptTags: ["us-gaap:IncomeTaxExpenseBenefit"],
    },
    //   {
    //     id: "dividends",
    //     title: "Dividends Paid",
    //     color: "green",
    //     tags: ["us-gaap:DividendsPaid"],
    //   },
    //   {
    //     id: "stock-buybacks",
    //     title: "Stock Buybacks",
    //     color: "green",
    //     tags: ["us-gaap:PaymentsForRepurchaseOfCommonStock"],
    //   }
  ],
  links: [
    {
      source: "revenue",
      target: "cost-of-goods-sold",
      order: 1,
      // value: 1,
      // type: "x",
      // condition: "positive",
      // valueCalculation: "min-source-target",
    },
    {
      source: "bank-account",
      target: "cost-of-goods-sold",
      order: 2,
    },
    {
      source: "revenue",
      target: "gross-profit",
      order: 3,
    },
    {
      source: "bank-account",
      target: "gross-profit",
      order: 4,
    },
    {
      source: "gross-profit",
      target: "operating-profit",
      order: 5,
    },
    {
      source: "gross-profit",
      target: "operating-expenses",
      order: 6,
    },
    {
      source: "bank-account",
      target: "operating-expenses",
      order: 7,
    },
    {
      source: "operating-expenses",
      target: "research-and-development",
      order: 8,
    },
    {
      source: "operating-expenses",
      target: "selling-general-and-administrative",
      order: 9,
    },
    {
      source: "operating-expenses",
      target: "impairment-of-long-lived-assets",
      order: 10,
    },
    {
      source: "operating-profit",
      target: "net-profit",
      order: 11,
    },
    {
      source: "operating-profit",
      target: "interest",
      order: 12,
    },
    {
      source: "operating-profit",
      target: "tax",
      order: 14,
    },
    {
      source: "bank-account",
      target: "tax",
      order: 15,
    },
    //   {
    //     source: "net-profit",
    //     target: "dividends",
    //   },
    //   {
    //     source: "bank-account",
    //     target: "dividends",
    //   },
  ],
};

const linkKey = (link: IncomeSankeyLink) => `${link.source}|${link.target}`;

/**
 * Merges two income sankey templates.
 * Nodes matched by id will be overridden by the override template.
 * Links matched by source and target will be overridden by the override template.
 * The nodes and links will be sorted by order.
 * @param defaultTemplate - The default income sankey template.
 * @param overrideTemplate - The override income sankey template.
 * @returns The merged income sankey template.
 */
const mergeIncomeSankeyTemplates = (
  defaultTemplate: IncomeSankeyTemplate,
  overrideTemplate?: IncomeSankeyTemplate
): IncomeSankeyTemplate => {
  if (!overrideTemplate) {
    return {
      nodes: [...defaultTemplate.nodes].sort((a, b) => a.order - b.order),
      links: [...defaultTemplate.links].sort((a, b) => a.order - b.order),
    };
  }

  const nodeMap = new Map<string, IncomeSankeyNode>();
  for (const node of defaultTemplate.nodes) {
    nodeMap.set(node.id, { ...node });
  }
  for (const node of overrideTemplate.nodes) {
    const existing = nodeMap.get(node.id);
    nodeMap.set(node.id, existing ? { ...existing, ...node } : { ...node });
  }
  const nodes = Array.from(nodeMap.values()).sort((a, b) => a.order - b.order);

  const linkMap = new Map<string, IncomeSankeyLink>();
  for (const link of defaultTemplate.links) {
    linkMap.set(linkKey(link), { ...link });
  }
  for (const link of overrideTemplate.links) {
    const key = linkKey(link);
    const existing = linkMap.get(key);
    linkMap.set(key, existing ? { ...existing, ...link } : { ...link });
  }
  const links = Array.from(linkMap.values()).sort((a, b) => a.order - b.order);

  return { nodes, links };
};

const getNodeValue = (
  node: IncomeSankeyNode | undefined,
  valuesByConcept: Record<string, number>,
  valuesByConceptPrior?: Record<string, number>
): number => {
  if (!node) {
    return 0;
  }
  const values =
    node.usePriorPeriod && valuesByConceptPrior
      ? valuesByConceptPrior
      : valuesByConcept;
  const rawValue =
    node.conceptTags?.reduce((acc, tag) => {
      if (typeof tag === "string") {
        return acc + values[tag] || 0;
      } else {
        return (
          acc + (tag.action === "add" ? values[tag.tag] : -values[tag.tag] || 0)
        );
      }
    }, 0) || 0;
  return rawValue;
};

const getAbsoluteNodeValue = (
  node: IncomeSankeyNode | undefined,
  valuesByConcept: Record<string, number>,
  valuesByConceptPrior?: Record<string, number>
): number =>
  Math.abs(getNodeValue(node, valuesByConcept, valuesByConceptPrior));

/** Format a number as US dollar currency with negative values in parentheses. */
const formatNodeValueLabel = (value: number): string => {
  if (value >= 0) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  }
  return `(${new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(-value)})`;
};

const adjustConceptValues = (
  tags: IncomeSankeyNodeTag[],
  value: number,
  valuesByConcept: Record<string, number>
) => {
  if (!tags) {
    return;
  }
  tags.forEach((t) => {
    if (typeof t === "string") {
      valuesByConcept[t] -= value;
    } else {
      t.action === "add"
        ? (valuesByConcept[t.tag] -= value)
        : (valuesByConcept[t.tag] += value);
    }
  });
};

const getNodeTitle = (
  node: IncomeSankeyNode,
  companyFactsResponse: CompanyFactsResponse,
  value?: number
): string => {
  const useWhenNegative = value !== undefined && value < 0;
  if (useWhenNegative && node.titleWhenNegative) {
    return node.titleWhenNegative;
  }
  if (node.title) {
    return node.title;
  }
  const { concepts } = companyFactsResponse;
  for (const tag of node.conceptTags) {
    if (typeof tag === "string") {
      const concept = concepts.find((c) => c.tag === tag);
      if (concept) {
        return concept.label;
      }
    }
  }
  return node.id;
};

const getNodeColor = (
  node: IncomeSankeyNode,
  value: number
): string | undefined =>
  value < 0 && node.colorWhenNegative !== undefined
    ? node.colorWhenNegative
    : node.color;

/** Returns the period immediately before the given period when periods are ordered by end_date descending. */
const getPriorPeriod = (
  periods: FactPeriod[],
  periodId: string
): FactPeriod | null => {
  const sorted = [...periods].sort(
    (a, b) => new Date(b.end_date).getTime() - new Date(a.end_date).getTime()
  );
  const idx = sorted.findIndex((p) => p.id === periodId);
  return idx >= 0 && idx < sorted.length - 1 ? sorted[idx + 1] : null;
};

export const getIncomeSankey = (
  companyFactsResponse: CompanyFactsResponse,
  periodId: string,
  incomeSankeyTemplateOverride?: IncomeSankeyTemplate
): SankeyGraph => {
  const { periods } = companyFactsResponse;
  const period = periods.find((p) => p.id === periodId);
  if (!period) {
    throw new Error(`Period ${periodId} not found`);
  }
  const priorPeriod = getPriorPeriod(periods, periodId);
  const incomeSankeyTemplate = mergeIncomeSankeyTemplates(
    defaultIncomeSankeyTemplate,
    incomeSankeyTemplateOverride
  );
  const { facts } = period;
  const valuesByConcept: Record<string, number> = facts.reduce(
    (acc: Record<string, number>, fact) => {
      acc[fact.concept] = Number.parseFloat(fact.value);
      return acc;
    },
    {}
  );
  const valuesByConceptPrior: Record<string, number> | undefined = priorPeriod
    ? priorPeriod.facts.reduce(
        (acc: Record<string, number>, fact) => {
          acc[fact.concept] = Number.parseFloat(fact.value);
          return acc;
        },
        {} as Record<string, number>
      )
    : undefined;
  const incomeSankeyNodes: IncomeSankeyNode[] =
    incomeSankeyTemplate.nodes.filter(
      (n) =>
        getAbsoluteNodeValue(n, valuesByConcept, valuesByConceptPrior) !== 0
    );
  const nodeValues: Record<string, number> = {};
  for (const n of incomeSankeyNodes) {
    nodeValues[n.id] = getNodeValue(n, valuesByConcept, valuesByConceptPrior);
  }
  const nodes: SankeyNode[] = incomeSankeyNodes.map((n) => {
    const value = nodeValues[n.id];
    return {
      id: n.id,
      title: getNodeTitle(n, companyFactsResponse, value),
      color: getNodeColor(n, value),
      value,
      valueLabel: formatNodeValueLabel(value),
    };
  });
  const filteredLinks: IncomeSankeyLink[] = incomeSankeyTemplate.links.filter(
    (l) => {
      return (
        nodes.some((n) => n.id === l.source) &&
        nodes.some((n) => n.id === l.target)
      );
    }
  );
  const links: SankeyLink[] = filteredLinks.map((l) => {
    const sourceNode = incomeSankeyNodes.find((n) => n.id === l.source);
    const targetNode = incomeSankeyNodes.find((n) => n.id === l.target);
    const sourceValue = getAbsoluteNodeValue(
      sourceNode,
      valuesByConcept,
      valuesByConceptPrior
    );
    const targetValue = getAbsoluteNodeValue(
      targetNode,
      valuesByConcept,
      valuesByConceptPrior
    );
    const value = Math.min(sourceValue, targetValue);
    if (value !== 0) {
      if (sourceNode)
        adjustConceptValues(
          sourceNode.conceptTags || [],
          value,
          sourceNode.usePriorPeriod && valuesByConceptPrior
            ? valuesByConceptPrior
            : valuesByConcept
        );
      if (targetNode)
        adjustConceptValues(
          targetNode.conceptTags || [],
          value,
          targetNode.usePriorPeriod && valuesByConceptPrior
            ? valuesByConceptPrior
            : valuesByConcept
        );
    }

    return { source: l.source, target: l.target, value: value, color: "black" };
  });
  return { nodes, links };
};
