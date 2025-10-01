import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  BarChart3,
  BookOpen,
  Calculator,
  CheckCircle,
  Copy,
  DollarSign,
  Info,
  Menu,
  RefreshCw,
  Search,
  Shield,
  SortAsc,
  SortDesc,
  Target,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import PropTypes from "prop-types";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sidebar } from "./shared";

// ConceptCard component
const ConceptCard = ({ concept }) => {
  const [expanded, setExpanded] = useState(false);
  const IconComponent = concept.icon;

  return (
    <div className="card p-6 hover:shadow-lg transition-all duration-200">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-primary-600/20 rounded-lg flex items-center justify-center">
            <IconComponent className="w-5 h-5 text-primary-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-100">
              {concept.name}
            </h3>
            <span
              className={`inline-block px-2 py-1 rounded-full text-xs font-medium ${getCategoryColor(
                concept.category
              )}`}
            >
              {categories.find((cat) => cat.value === concept.category)?.label}
            </span>
          </div>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-gray-400 hover:text-gray-200 transition-colors"
        >
          {expanded ? (
            <SortAsc className="w-5 h-5" />
          ) : (
            <SortDesc className="w-5 h-5" />
          )}
        </button>
      </div>

      <p className="text-gray-300 mb-4">{concept.description}</p>

      {expanded && (
        <div className="space-y-4 pt-4 border-t border-gray-700">
          {/* Formula */}
          <div className="bg-dark-800 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-gray-200 mb-2 flex items-center">
              <Calculator className="w-4 h-4 mr-2" />
              Formula
            </h4>
            <code className="text-sm text-primary-300 font-mono">
              {concept.formula}
            </code>
          </div>

          {/* Example */}
          <div className="bg-dark-800 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-gray-200 mb-2 flex items-center">
              <Info className="w-4 h-4 mr-2" />
              Example
            </h4>
            <p className="text-sm text-gray-300">{concept.example}</p>
          </div>

          {/* Interpretation */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-gray-200 flex items-center">
              <Target className="w-4 h-4 mr-2" />
              How to Interpret
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-3">
                <div className="flex items-center mb-2">
                  <CheckCircle className="w-4 h-4 text-green-400 mr-2" />
                  <span className="text-sm font-medium text-green-300">
                    Good Values
                  </span>
                </div>
                <p className="text-xs text-green-200">
                  {concept.interpretation.good}
                </p>
              </div>

              <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-3">
                <div className="flex items-center mb-2">
                  <AlertTriangle className="w-4 h-4 text-red-400 mr-2" />
                  <span className="text-sm font-medium text-red-300">
                    Bad Values
                  </span>
                </div>
                <p className="text-xs text-red-200">
                  {concept.interpretation.bad}
                </p>
              </div>

              <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-3">
                <div className="flex items-center mb-2">
                  <ArrowRight className="w-4 h-4 text-blue-400 mr-2" />
                  <span className="text-sm font-medium text-blue-300">
                    Decision Making
                  </span>
                </div>
                <p className="text-xs text-blue-200">
                  {concept.interpretation.decision}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Helper function for category colors
const getCategoryColor = (category) => {
  const colors = {
    performance: "text-green-400 bg-green-400/20",
    risk: "text-red-400 bg-red-400/20",
    portfolio: "text-blue-400 bg-blue-400/20",
    transactions: "text-yellow-400 bg-yellow-400/20",
    technical: "text-purple-400 bg-purple-400/20",
  };
  return colors[category] || "text-gray-400 bg-gray-400/20";
};

// Categories array
const categories = [
  { value: "all", label: "All Concepts", icon: BookOpen },
  { value: "performance", label: "Performance Metrics", icon: TrendingUp },
  { value: "risk", label: "Risk Metrics", icon: Shield },
  { value: "portfolio", label: "Portfolio Management", icon: Target },
  { value: "transactions", label: "Transaction Types", icon: DollarSign },
  { value: "technical", label: "Technical Indicators", icon: Activity },
];

const FinancialConcepts = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [sortBy, setSortBy] = useState("name");
  const [sortOrder, setSortOrder] = useState("asc");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);

  // Mobile detection
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 1024);
    };

    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // Comprehensive financial concepts data
  const concepts = useMemo(
    () => [
      // Core Performance Metrics
      {
        name: "Cost Basis",
        category: "performance",
        icon: Calculator,
        description:
          "The original value of an asset for tax purposes, usually the purchase price adjusted for commissions and other expenses.",
        calculation: "Purchase Price + Commissions + Fees",
        interpretation: {
          good: "Lower cost basis relative to current market price indicates better entry point",
          bad: "High cost basis means you paid a lot and need higher selling price for profit",
          decision:
            "Use cost basis to determine tax implications and profit/loss calculations",
        },
        formula: "Cost Basis = Purchase Price + Transaction Costs",
        example:
          "Bought 100 shares at $50 + $10 commission = $5,010 cost basis",
      },
      {
        name: "Unrealized Profit & Loss (P&L)",
        category: "performance",
        icon: TrendingUp,
        description:
          'The "on-paper" profit or loss you have on an asset you still own. It\'s the difference between the current market value and the cost basis.',
        calculation: "Current Market Value - Cost Basis",
        interpretation: {
          good: "Positive unrealized P&L shows profitable holdings",
          bad: "Negative unrealized P&L indicates current losses",
          decision:
            "Large unrealized gains might prompt selling to lock in profits; large losses might signal re-evaluation",
        },
        formula: "Unrealized P&L = (Current Price - Cost Basis) × Quantity",
        example:
          "100 shares at $60 current price, $50 cost basis = $1,000 unrealized gain",
      },
      {
        name: "Cumulative Return",
        category: "performance",
        icon: BarChart3,
        description:
          "The total change in an investment's value over a specific period, expressed as a percentage.",
        calculation: "(Ending Value - Beginning Value) / Beginning Value × 100",
        interpretation: {
          good: "Positive cumulative return indicates growth over the period",
          bad: "Negative cumulative return shows decline over the period",
          decision:
            "Useful for understanding absolute performance from start to end date",
        },
        formula: "Cumulative Return = (Ending Value / Beginning Value) - 1",
        example:
          "Investment grew from $10,000 to $11,500 = 15% cumulative return",
      },
      {
        name: "Annualized Return",
        category: "performance",
        icon: TrendingUp,
        description:
          "The geometric average amount of money earned by an investment each year over a given time period. It smooths out volatility to show steady growth rate.",
        calculation: "((Ending Value / Beginning Value)^(1/years)) - 1",
        interpretation: {
          good: "Higher annualized return indicates better long-term performance",
          bad: "Lower annualized return suggests underperformance",
          decision:
            "Compare against benchmarks (like S&P 500) or other investment opportunities",
        },
        formula:
          "Annualized Return = (Ending Value / Beginning Value)^(1/n) - 1",
        example: "Investment grew 50% over 3 years = 14.47% annualized return",
      },
      {
        name: "Compound Annual Growth Rate (CAGR)",
        category: "performance",
        icon: Activity,
        description:
          "The geometric progression ratio that provides a constant rate of return over the time period. Best for comparing investments over different time periods.",
        calculation: "(Ending Value / Beginning Value)^(1/years) - 1",
        interpretation: {
          good: "Higher CAGR indicates better long-term growth",
          bad: "Lower CAGR suggests slower growth or underperformance",
          decision:
            "Best metric for comparing investments held for different time periods",
        },
        formula: "CAGR = (Ending Value / Beginning Value)^(1/n) - 1",
        example: "Portfolio grew from $100K to $200K in 5 years = 14.87% CAGR",
      },
      {
        name: "Time-Weighted Return (TWR)",
        category: "performance",
        icon: Target,
        description:
          "The compound rate of growth that eliminates the distorting effects of cash flows. Shows how an initial dollar invested would have grown.",
        calculation:
          "Links sub-period returns geometrically: [(1 + R1) × (1 + R2) × ... × (1 + Rn)] - 1",
        interpretation: {
          good: "Higher TWR indicates better investment manager performance",
          bad: "Lower TWR suggests poor investment decisions or market timing",
          decision:
            "Best for evaluating investment manager skill, removes impact of cash flow timing",
        },
        formula: "TWR = [(1 + R1) × (1 + R2) × ... × (1 + Rn)] - 1",
        example:
          "If TWR > MWR, your timing has been suboptimal; if TWR < MWR, your timing has been beneficial",
      },
      {
        name: "Money-Weighted Return (MWR)",
        category: "performance",
        icon: DollarSign,
        description:
          "The actual return an investor has earned, taking into account the timing and size of all cash flows. Essentially the internal rate of return.",
        calculation:
          "Rate that sets present value of all cash inflows equal to present value of all cash outflows",
        interpretation: {
          good: "Higher MWR indicates better personal investment performance",
          bad: "Lower MWR suggests poor timing of contributions/withdrawals",
          decision:
            "Reflects your personal investment experience and timing decisions",
        },
        formula: "MWR = IRR where NPV = 0",
        example:
          "MWR of 8% means your specific investment activities resulted in 8% annualized return",
      },
      {
        name: "Extended Internal Rate of Return (XIRR)",
        category: "performance",
        icon: Calculator,
        description:
          "A flexible version of MWR that calculates the internal rate of return for irregular cash flows. Most practical for individual investors.",
        calculation:
          "Iterative calculation that finds the rate where NPV = 0 for irregular cash flows",
        interpretation: {
          good: "Higher XIRR indicates better personal investment performance",
          bad: "Lower XIRR suggests poor timing or investment choices",
          decision:
            "Most accurate measure of personal returns when cash flows are sporadic",
        },
        formula: "XIRR = IRR for irregular cash flows",
        example:
          "XIRR of 12% means your investments grew at 12% annually considering all transaction timing",
      },

      // Risk Metrics
      {
        name: "Volatility (Standard Deviation)",
        category: "risk",
        icon: Activity,
        description:
          "A statistical measure of the dispersion of returns. Measures how much the price swings up and down.",
        calculation: "Square root of the variance of returns",
        interpretation: {
          good: "Lower volatility indicates more stable, predictable returns",
          bad: "Higher volatility means more risk and uncertainty",
          decision:
            "Conservative investors prefer low volatility; aggressive investors may accept high volatility for higher returns",
        },
        formula: "σ = √(Σ(Ri - R̄)² / n)",
        example:
          "30% annualized volatility is much riskier than 10% volatility",
      },
      {
        name: "Sharpe Ratio",
        category: "risk",
        icon: Shield,
        description:
          "Measures an investment's excess return per unit of risk (volatility). Answers: \"Am I getting paid enough for the risk I'm taking?\"",
        calculation:
          "(Portfolio Return - Risk-free Rate) / Portfolio Volatility",
        interpretation: {
          good: "> 2: Very good; 1-1.99: Good; < 1: Not great return for risk taken",
          bad: "Negative Sharpe ratio indicates returns below risk-free rate",
          decision:
            "Higher Sharpe ratio is better on a risk-adjusted basis when comparing portfolios",
        },
        formula: "Sharpe Ratio = (Rp - Rf) / σp",
        example:
          "Portfolio return 12%, risk-free rate 3%, volatility 15% = 0.6 Sharpe ratio",
      },
      {
        name: "Maximum Drawdown (MDD)",
        category: "risk",
        icon: TrendingDown,
        description:
          "The largest peak-to-trough decline in portfolio value. Measures the biggest loss from a previous high point.",
        calculation:
          "Maximum percentage decline from any peak to subsequent trough",
        interpretation: {
          good: "Lower maximum drawdown indicates better downside protection",
          bad: "Higher maximum drawdown means larger potential losses",
          decision:
            "Can you stomach a 25% drop without panic selling? If not, portfolio might be too risky",
        },
        formula: "MDD = max((Peak - Trough) / Peak)",
        example: "Portfolio dropped from $100K to $75K = 25% maximum drawdown",
      },
      {
        name: "Value at Risk (VaR)",
        category: "risk",
        icon: AlertTriangle,
        description:
          "A statistic that quantifies the extent of possible financial losses within a specific time frame and confidence level.",
        calculation:
          "Statistical measure of potential loss at a given confidence level",
        interpretation: {
          good: "Lower VaR indicates lower potential losses",
          bad: "Higher VaR means greater potential for significant losses",
          decision:
            "VaR helps in risk management by putting dollar amounts on potential losses",
        },
        formula: "VaR = μ - (σ × Z-score)",
        example:
          "1-day 95% VaR of $1,000 means 5% chance of losing at least $1,000 tomorrow",
      },
      {
        name: "Beta",
        category: "risk",
        icon: BarChart3,
        description:
          "Measures a stock's or portfolio's volatility in relation to the overall market (usually S&P 500).",
        calculation: "Covariance(Portfolio, Market) / Variance(Market)",
        interpretation: {
          good: "Beta = 1: Moves with market; Beta < 1: Less volatile than market; Beta > 1: More volatile than market",
          bad: "Very high beta (>2) indicates extreme volatility and risk",
          decision:
            "Add low-beta assets to reduce market risk; add high-beta assets to amplify market gains",
        },
        formula: "β = Cov(Rp, Rm) / Var(Rm)",
        example:
          "Tech stock with beta 1.5 rises 1.5% when market rises 1%; utility with beta 0.6 rises 0.6%",
      },
      {
        name: "Correlation",
        category: "risk",
        icon: Activity,
        description:
          "A statistical measure of how two securities move in relation to each other. Ranges from -1 to +1.",
        calculation:
          "Covariance(X,Y) / (Standard Deviation(X) × Standard Deviation(Y))",
        interpretation: {
          good: "Low or negative correlation helps with diversification",
          bad: "High positive correlation (>0.8) means poor diversification",
          decision:
            "Combine assets with low/negative correlations to reduce portfolio risk",
        },
        formula: "ρ = Cov(X,Y) / (σx × σy)",
        example:
          "Correlation of +0.9 means assets move almost in lockstep; -0.5 means they move in opposite directions",
      },

      // Portfolio Management Concepts
      {
        name: "Asset Allocation",
        category: "portfolio",
        icon: Target,
        description:
          "The process of setting target percentages for different asset classes (e.g., 60% stocks, 40% bonds) in your portfolio.",
        calculation: "Percentage of total portfolio value in each asset class",
        interpretation: {
          good: "Proper allocation balances risk and return based on your goals",
          bad: "Poor allocation can lead to excessive risk or missed opportunities",
          decision:
            "Set allocation based on risk tolerance, time horizon, and financial goals",
        },
        formula: "Allocation % = (Asset Value / Total Portfolio Value) × 100",
        example:
          "Portfolio: $100K total, $60K stocks, $40K bonds = 60/40 allocation",
      },
      {
        name: "Allocation Drift",
        category: "portfolio",
        icon: TrendingUp,
        description:
          "Over time, assets that perform well grow to represent a larger percentage of your portfolio, causing allocation to drift away from targets.",
        calculation: "Current Allocation - Target Allocation",
        interpretation: {
          good: "Small drift (<5%) is normal and manageable",
          bad: "Large drift (>10%) changes your risk profile significantly",
          decision:
            "Monitor drift and rebalance when it exceeds your threshold",
        },
        formula: "Drift = |Current % - Target %|",
        example:
          "Target 60% stocks, but stocks grew to 70% = 10% allocation drift",
      },
      {
        name: "Rebalancing",
        category: "portfolio",
        icon: RefreshCw,
        description:
          "The process of buying or selling assets to return your portfolio to its target allocation.",
        calculation:
          "Sell overperforming assets, buy underperforming assets to restore targets",
        interpretation: {
          good: "Regular rebalancing maintains your desired risk level",
          bad: "Infrequent rebalancing can lead to unintended risk exposure",
          decision:
            "Rebalance quarterly, annually, or when drift exceeds threshold",
        },
        formula: "Rebalance when |Current % - Target %| > Threshold",
        example:
          "Sell 10% of stocks, buy 10% more bonds to return to 60/40 allocation",
      },
      {
        name: "Diversification",
        category: "portfolio",
        icon: Shield,
        description:
          "The practice of spreading investments across different assets, sectors, or regions to reduce risk.",
        calculation: "Number and variety of different investments in portfolio",
        interpretation: {
          good: "Higher diversification reduces unsystematic risk",
          bad: "Over-diversification can dilute returns without meaningful risk reduction",
          decision:
            "Diversify across asset classes, sectors, and geographies, but don't over-diversify",
        },
        formula: "Risk Reduction = 1 - (1/n)",
        example:
          "Portfolio with 20+ stocks reduces company-specific risk by ~95%",
      },

      // Transaction Types
      {
        name: "Buy Transaction",
        category: "transactions",
        icon: TrendingUp,
        description:
          "Purchase of assets that increases your position in a security.",
        calculation: "Total Cost = Quantity × Price + Fees",
        interpretation: {
          good: "Buying at low prices relative to intrinsic value",
          bad: "Buying at market peaks or overvalued prices",
          decision:
            "Consider dollar-cost averaging and fundamental analysis before buying",
        },
        formula: "Total Cost = (Quantity × Price) + Fees",
        example: "Buy 100 shares at $50 + $10 commission = $5,010 total cost",
      },
      {
        name: "Sell Transaction",
        category: "transactions",
        icon: TrendingDown,
        description:
          "Sale of assets that decreases your position in a security.",
        calculation: "Proceeds = Quantity × Price - Fees",
        interpretation: {
          good: "Selling at high prices or when fundamentals deteriorate",
          bad: "Selling at market lows or due to panic",
          decision:
            "Consider tax implications and rebalancing needs before selling",
        },
        formula: "Proceeds = (Quantity × Price) - Fees",
        example: "Sell 100 shares at $60 - $10 commission = $5,990 proceeds",
      },
      {
        name: "Dividend",
        category: "transactions",
        icon: DollarSign,
        description:
          "Payment made by a corporation to its shareholders, usually as a distribution of profits.",
        calculation: "Dividend Income = Shares Owned × Dividend Per Share",
        interpretation: {
          good: "Regular dividends provide income and indicate company stability",
          bad: "Cut dividends may signal financial distress",
          decision: "Consider dividend yield, growth rate, and sustainability",
        },
        formula: "Dividend Income = Shares × Dividend Per Share",
        example: "100 shares × $2.50 dividend = $250 dividend income",
      },
      {
        name: "Stock Split",
        category: "transactions",
        icon: Copy,
        description:
          "Corporate action that increases the number of shares outstanding while proportionally reducing the price per share.",
        calculation: "New Shares = Old Shares × Split Ratio",
        interpretation: {
          good: "Stock splits often indicate company growth and confidence",
          bad: "Reverse splits may signal financial difficulties",
          decision: "Splits don't change total value, just number of shares",
        },
        formula: "New Price = Old Price / Split Ratio",
        example: "2:1 split: 100 shares at $100 become 200 shares at $50",
      },
      {
        name: "Realized Gain/Loss",
        category: "transactions",
        icon: Calculator,
        description:
          "The actual profit or loss from selling an asset, which becomes taxable income.",
        calculation: "Proceeds - Cost Basis",
        interpretation: {
          good: "Realized gains increase your wealth and taxable income",
          bad: "Realized losses reduce wealth but may provide tax benefits",
          decision:
            "Consider tax-loss harvesting and long-term vs short-term capital gains",
        },
        formula: "Realized P&L = Proceeds - Cost Basis",
        example: "Sell for $6,000, cost basis $5,000 = $1,000 realized gain",
      },

      // Technical Indicators
      {
        name: "RSI (Relative Strength Index)",
        category: "technical",
        icon: Activity,
        description:
          "A momentum oscillator that measures the speed and magnitude of price changes to identify overbought or oversold conditions.",
        calculation:
          "100 - (100 / (1 + RS)) where RS = Average Gain / Average Loss",
        interpretation: {
          good: "RSI 30-70 indicates normal market conditions",
          bad: "RSI > 70 suggests overbought; RSI < 30 suggests oversold",
          decision: "Use RSI to identify potential reversal points",
        },
        formula: "RSI = 100 - (100 / (1 + RS))",
        example:
          "RSI of 80 suggests stock may be overbought and due for correction",
      },
      {
        name: "MACD (Moving Average Convergence Divergence)",
        category: "technical",
        icon: BarChart3,
        description:
          "A trend-following momentum indicator that shows the relationship between two moving averages of prices.",
        calculation:
          "MACD Line = EMA(12) - EMA(26); Signal Line = EMA(9) of MACD",
        interpretation: {
          good: "MACD above signal line suggests bullish momentum",
          bad: "MACD below signal line suggests bearish momentum",
          decision: "Look for crossovers and divergences for trading signals",
        },
        formula: "MACD = EMA(12) - EMA(26)",
        example: "MACD crossing above signal line often indicates buy signal",
      },
      {
        name: "Moving Average",
        category: "technical",
        icon: TrendingUp,
        description:
          "A technical indicator that smooths out price data by creating a constantly updated average price over a specific time period.",
        calculation: "Sum of closing prices over period / Number of periods",
        interpretation: {
          good: "Price above moving average suggests uptrend",
          bad: "Price below moving average suggests downtrend",
          decision:
            "Use multiple timeframes (50-day, 200-day) for trend analysis",
        },
        formula: "MA = (P1 + P2 + ... + Pn) / n",
        example:
          "Stock trading above 200-day moving average indicates long-term uptrend",
      },
    ],
    []
  );

  const filteredAndSortedConcepts = useMemo(() => {
    let filtered = concepts.filter((concept) => {
      const matchesSearch =
        concept.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        concept.description.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesCategory =
        selectedCategory === "all" || concept.category === selectedCategory;
      return matchesSearch && matchesCategory;
    });

    return filtered.sort((a, b) => {
      let comparison = 0;
      switch (sortBy) {
        case "name":
          comparison = a.name.localeCompare(b.name);
          break;
        case "category":
          comparison = a.category.localeCompare(b.category);
          break;
        default:
          comparison = a.name.localeCompare(b.name);
      }
      return sortOrder === "asc" ? comparison : -comparison;
    });
  }, [concepts, searchQuery, selectedCategory, sortBy, sortOrder]);

  return (
    <div className="min-h-screen gradient-bg flex">
      {/* Mobile sidebar overlay */}
      {isMobile && sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Shared Sidebar */}
      <Sidebar
        currentView="concepts"
        portfolios={[]}
        onRefresh={() => {}}
        onQuickAction={() => {}}
        isMobile={isMobile}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Top Header */}
        <header className="bg-dark-900/80 backdrop-blur-sm border-b border-dark-700 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              {/* Mobile menu button */}
              {isMobile && (
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="text-gray-400 hover:text-gray-200 transition-colors"
                >
                  <Menu className="w-6 h-6" />
                </button>
              )}

              {/* Back button */}
              <button
                onClick={() => navigate(-1)}
                className="flex items-center space-x-2 text-gray-400 hover:text-gray-200 transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
                <span>Back</span>
              </button>

              <div className="flex items-center space-x-3">
                <BookOpen className="w-8 h-8 text-primary-400" />
                <div>
                  <h1 className="text-2xl font-bold text-gray-100">
                    Financial Concepts Guide
                  </h1>
                  <p className="text-sm text-gray-400">
                    Comprehensive guide to financial metrics and concepts
                  </p>
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 overflow-auto">
          <div className="container mx-auto px-4 py-8">
            {/* Search and Filters */}
            <div className="card p-6 mb-8">
              <div className="flex flex-col lg:flex-row gap-4">
                {/* Search */}
                <div className="flex-1">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                    <input
                      type="text"
                      placeholder="Search financial concepts..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full pl-10 pr-4 py-3 bg-dark-800 border border-gray-600 rounded-lg text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>
                </div>

                {/* Category Filter */}
                <div className="lg:w-64">
                  <select
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    className="w-full px-4 py-3 bg-dark-800 border border-gray-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  >
                    {categories.map((category) => (
                      <option key={category.value} value={category.value}>
                        {category.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Sort */}
                <div className="lg:w-48">
                  <select
                    value={`${sortBy}-${sortOrder}`}
                    onChange={(e) => {
                      const [newSortBy, newSortOrder] =
                        e.target.value.split("-");
                      setSortBy(newSortBy);
                      setSortOrder(newSortOrder);
                    }}
                    className="w-full px-4 py-3 bg-dark-800 border border-gray-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  >
                    <option value="name-asc">Name A-Z</option>
                    <option value="name-desc">Name Z-A</option>
                    <option value="category-asc">Category A-Z</option>
                    <option value="category-desc">Category Z-A</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
              <div className="card p-4 text-center">
                <div className="text-2xl font-bold text-gray-100">
                  {concepts.length}
                </div>
                <div className="text-sm text-gray-400">Total Concepts</div>
              </div>
              <div className="card p-4 text-center">
                <div className="text-2xl font-bold text-green-400">
                  {concepts.filter((c) => c.category === "performance").length}
                </div>
                <div className="text-sm text-gray-400">Performance Metrics</div>
              </div>
              <div className="card p-4 text-center">
                <div className="text-2xl font-bold text-red-400">
                  {concepts.filter((c) => c.category === "risk").length}
                </div>
                <div className="text-sm text-gray-400">Risk Metrics</div>
              </div>
              <div className="card p-4 text-center">
                <div className="text-2xl font-bold text-blue-400">
                  {concepts.filter((c) => c.category === "portfolio").length}
                </div>
                <div className="text-sm text-gray-400">Portfolio Concepts</div>
              </div>
              <div className="card p-4 text-center">
                <div className="text-2xl font-bold text-purple-400">
                  {concepts.filter((c) => c.category === "technical").length}
                </div>
                <div className="text-sm text-gray-400">
                  Technical Indicators
                </div>
              </div>
            </div>

            {/* Concepts Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {filteredAndSortedConcepts.map((concept, index) => (
                <ConceptCard key={index} concept={concept} />
              ))}
            </div>

            {/* No Results */}
            {filteredAndSortedConcepts.length === 0 && (
              <div className="text-center py-12">
                <Search className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-300 mb-2">
                  No Concepts Found
                </h3>
                <p className="text-gray-500">
                  Try adjusting your search terms or category filter.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// PropTypes for ConceptCard component
ConceptCard.propTypes = {
  concept: PropTypes.shape({
    name: PropTypes.string.isRequired,
    category: PropTypes.string.isRequired,
    icon: PropTypes.elementType.isRequired,
    description: PropTypes.string.isRequired,
    formula: PropTypes.string.isRequired,
    example: PropTypes.string.isRequired,
    interpretation: PropTypes.shape({
      good: PropTypes.string.isRequired,
      bad: PropTypes.string.isRequired,
      decision: PropTypes.string.isRequired,
    }).isRequired,
  }).isRequired,
};

export default FinancialConcepts;
