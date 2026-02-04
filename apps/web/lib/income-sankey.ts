import { CompanyFactsResponse } from './api';
import { SankeyGraph } from 'd3-sankey-diagram';

type IncomeSankeyNode = {
  /** Unique income sankey node id. */  
  id: string
  /** Visual order of the node in the graph. Lower numbers are closer to the top of the graph with respect to nodes at the same level.
  */
  order: number
  /** Optional title for the node. If not provided, will use title from company fact concept identified by tags.*/
  title?: string
  /** Optional color for the node. */
  color?: string
  /** Optional icon for the node. */
  icon?: string
  /** Concept tags identifying which company facts to extract values from.
   * If not provided or with no value, the node will not be included in the graph.
   * If provided with a value, the node will be included in the graph and the value will be extracted from the CompanyFact data.
   * If the node has multiple tags, the value will be the sum of the values extracted from the CompanyFact data.
   * If a tag has an action, the value will be altered appropriately (added or subtracted). */
  tags?: IncomeSankeyNodeTag[]
}

type IncomeSankeyNodeTag = string | {
  tag: string
  action?: "add" | "subtract"
}

type IncomeSankeyLink = {
  /** Source income sankey node id. */
  source: string
  /** Target income sankey node id. */
  target: string
  /** Order in which amounts flow from sources to targets. For example if revenue and bank-account are both sources for cost-of-goods-sold, 
   * the order of `revenue => cost-of-goods-sold` should be less than the order of `bank-account => cost-of-goods-sold` for revenue to be 
   * the primary source. That way bank-account will only be a source if revenue is less than cost-of-goods-sold.
  */
  order: number
}

type IncomeSankeyTemplate = {
  nodes: IncomeSankeyNode[]
  links: IncomeSankeyLink[]
}

const incomeSankeyTemplate: IncomeSankeyTemplate = {
    nodes: [
      {
        id: "revenue",
        order: 1,
        title: "Revenue",
        color: "blue",
        tags: ["us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"],
      },
      {
        id: "bank-account",
        order: 2,
        title: "Bank Account",
        color: "grey",
      },
      {
        id: "cost-of-goods-sold",
        order: 3,
        title: "Cost of Goods Sold",
        color: "red",
        tags: ["us-gaap:CostOfGoodsAndServicesSold"],
      },
      {
        id: "gross-profit",
        order: 4,
        title: "Gross Profit",
        color: "green",
        tags: ["us-gaap:GrossProfit"],
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
        title: "Operating Profit (EBIT)",
        color: "green",
        tags: ["us-gaap:OperatingIncomeLoss"],
      },
      {
        id: "net-profit",
        order: 6,
        title: "Net Profit (EAT)",
        color: "green",
        tags: ["us-gaap:NetIncomeLoss"],
      },
      {
        id: "operating-expenses",
        order: 7,
        title: "Operating Expenses",
        color: "red",
        tags: ["us-gaap:CostsAndExpenses"],
      },
      {
        id: "research-and-development",
        order: 8,
        title: "Research and Development",
        color: "red",
        tags: ["us-gaap:ResearchAndDevelopmentExpense"],
      },
      {
        id: "selling-general-and-administrative",
        order: 9,
        title: "Selling, General and Administrative",
        color: "red",
        tags: ["us-gaap:SellingGeneralAndAdministrativeExpense"],
      },
      {
        id: "impairment-of-long-lived-assets",
        order: 10,
        title: "Other Expenses",
        color: "red",
        tags: ["us-gaap:ImpairmentOfLongLivedAssetsHeldForUse"],
      },
      {
        id: "interest",
        order: 11,
        title: "Interest",
        color: "red",
        tags: [
          "us-gaap:InterestExpenseNonoperating",
          {tag: "us-gaap:InvestmentIncomeInterest",action: "subtract"},
        ],
      },
      {
        id: "tax",
        order: 12,
        title: "Tax",
        color: "red",
        tags: ["us-gaap:IncomeTaxExpenseBenefit"],
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
        source: "bank-account",
        target: "interest",
        order: 13,
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

export const getIncomeSankey = (companyFactsResponse: CompanyFactsResponse, periodId: string, incomeSankeyOverride?: IncomeSankeyTemplate): SankeyGraph => {
    const { periods } = companyFactsResponse
    const period = periods.find((p) => p.id === periodId)
    if (!period) {
        throw new Error(`Period ${periodId} not found`)
    }
    const { facts } = period
    const sankeyJson: SankeyGraph = {
        nodes: facts.map((f) => ({ id: f.concept, name: f.concept })),
    }
    return sankeyJson
}