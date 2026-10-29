import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Building2,
  Calculator,
  CheckCircle,
  DollarSign,
  Info,
  Menu,
  Receipt,
  Search,
  Shield,
  SortAsc,
  SortDesc,
  Target,
  TrendingUp,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router";

import { useShell } from "../app/chrome";
import useIsMobile from "../hooks/useIsMobile";
import { GUIDE_CATEGORIES, METRIC_GUIDE } from "../shared/metricGuide";

const CATEGORY_STYLE = {
  performance: { icon: TrendingUp, color: "text-green-400 bg-green-400/20" },
  risk: { icon: Shield, color: "text-red-400 bg-red-400/20" },
  portfolio: { icon: Target, color: "text-blue-400 bg-blue-400/20" },
  tax: { icon: Receipt, color: "text-amber-400 bg-amber-400/20" },
  fundamentals: { icon: Building2, color: "text-cyan-400 bg-cyan-400/20" },
  technical: { icon: Activity, color: "text-purple-400 bg-purple-400/20" },
  transactions: { icon: DollarSign, color: "text-yellow-400 bg-yellow-400/20" },
};

const categoryLabel = (value) =>
  GUIDE_CATEGORIES.find((category) => category.value === value)?.label;

const Section = ({ icon: Icon, title, children, className = "bg-dark-800" }) => (
  <div className={`rounded-lg p-4 ${className}`}>
    <h4 className="text-sm font-semibold text-gray-200 mb-2 flex items-center">
      <Icon className="w-4 h-4 mr-2" />
      {title}
    </h4>
    {children}
  </div>
);

const ConceptCard = ({ concept, open }) => {
  const [expanded, setExpanded] = useState(open);
  const style = CATEGORY_STYLE[concept.category] || CATEGORY_STYLE.performance;
  const Icon = style.icon;

  useEffect(() => {
    if (open) setExpanded(true);
  }, [open]);

  return (
    <div
      id={concept.id}
      className={`card p-6 scroll-mt-24 transition-all duration-200 ${open ? "ring-2 ring-primary-500" : ""}`}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-primary-600/20 rounded-lg flex items-center justify-center">
            <Icon className="w-5 h-5 text-primary-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-100">{concept.name}</h3>
            <span className={`inline-block px-2 py-1 rounded-full text-xs font-medium ${style.color}`}>
              {categoryLabel(concept.category)}
            </span>
          </div>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          aria-expanded={expanded}
          aria-label={expanded ? `Collapse ${concept.name}` : `Expand ${concept.name}`}
          className="text-gray-400 hover:text-gray-200 transition-colors"
        >
          {expanded ? <SortAsc className="w-5 h-5" /> : <SortDesc className="w-5 h-5" />}
        </button>
      </div>

      <p className="text-gray-300 mb-2">{concept.short}</p>
      <p className="text-sm text-gray-400 mb-4">{concept.what}</p>

      {expanded && (
        <div className="space-y-4 pt-4 border-t border-gray-700">
          <Section icon={Calculator} title="How it is calculated here">
            <code className="text-sm text-primary-300 font-mono whitespace-pre-wrap">{concept.formula}</code>
          </Section>
          <Section icon={Info} title="Example">
            <p className="text-sm text-gray-300">{concept.example}</p>
          </Section>
          <Section icon={BookOpen} title="How to read it">
            <p className="text-sm text-gray-300">{concept.read}</p>
          </Section>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-3">
              <div className="flex items-center mb-2">
                <CheckCircle className="w-4 h-4 text-green-400 mr-2" />
                <span className="text-sm font-medium text-green-300">Good</span>
              </div>
              <p className="text-xs text-green-200">{concept.good}</p>
            </div>
            <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-3">
              <div className="flex items-center mb-2">
                <AlertTriangle className="w-4 h-4 text-red-400 mr-2" />
                <span className="text-sm font-medium text-red-300">Watch out</span>
              </div>
              <p className="text-xs text-red-200">{concept.bad}</p>
            </div>
            <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-3">
              <div className="flex items-center mb-2">
                <ArrowRight className="w-4 h-4 text-blue-400 mr-2" />
                <span className="text-sm font-medium text-blue-300">What it implies</span>
              </div>
              <p className="text-xs text-blue-200">{concept.implies}</p>
            </div>
          </div>

          {concept.caveat && (
            <p className="text-xs text-gray-500">
              <span className="font-medium text-gray-400">Note: </span>
              {concept.caveat}
            </p>
          )}
        </div>
      )}
    </div>
  );
};

const FinancialConcepts = () => {
  const navigate = useNavigate();
  const { hash } = useLocation();
  const { openSidebar } = useShell();
  const isMobile = useIsMobile(1024);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [sortBy, setSortBy] = useState("guide");
  const target = hash.replace("#", "");

  useEffect(() => {
    if (!target) return;
    setSearchQuery("");
    setSelectedCategory("all");
    const timer = setTimeout(
      () => document.getElementById(target)?.scrollIntoView({ behavior: "smooth", block: "start" }),
      50,
    );
    return () => clearTimeout(timer);
  }, [target]);

  const concepts = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    const filtered = METRIC_GUIDE.filter(
      (concept) =>
        (selectedCategory === "all" || concept.category === selectedCategory) &&
        (!query ||
          [concept.name, concept.short, concept.what].some((text) => text.toLowerCase().includes(query))),
    );
    if (sortBy === "guide") return filtered;
    const sorted = [...filtered].sort((a, b) => a.name.localeCompare(b.name));
    return sortBy === "name-desc" ? sorted.reverse() : sorted;
  }, [searchQuery, selectedCategory, sortBy]);

  return (
    <div className="min-h-screen gradient-bg flex">
      <div className="flex-1 min-w-0 flex flex-col">
        <header className="bg-dark-900/80 backdrop-blur-sm border-b border-dark-700 px-6 py-4">
          <div className="flex items-center space-x-4">
            {isMobile && (
              <button onClick={openSidebar} aria-label="Open menu" className="text-gray-400 hover:text-gray-200 transition-colors">
                <Menu className="w-6 h-6" />
              </button>
            )}
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
                <h1 className="text-2xl font-bold text-gray-100">Financial Concepts Guide</h1>
                <p className="text-sm text-gray-400">
                  Every number in the app: how it is calculated, how to read it, and what it implies for your portfolio
                </p>
              </div>
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-auto">
          <div className="container mx-auto px-4 py-8">
            <div className="card p-4 mb-6 text-sm text-gray-400">
              The good and bad ranges are common rules of thumb, not advice. Whether a number is good for you depends
              on your goals, horizon and how much of a fall you can sit through. Click the ⓘ next to any number in the
              app to jump here.
            </div>

            <div className="card p-6 mb-8">
              <div className="flex flex-col lg:flex-row gap-4">
                <div className="flex-1 relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                  <input
                    type="text"
                    aria-label="Search concepts"
                    placeholder="Search financial concepts..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 bg-dark-800 border border-gray-600 rounded-lg text-gray-100 placeholder-gray-400 focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                </div>
                <div className="lg:w-64">
                  <select
                    aria-label="Category"
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    className="w-full px-4 py-3 bg-dark-800 border border-gray-600 rounded-lg text-gray-100 focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  >
                    <option value="all">All concepts</option>
                    {GUIDE_CATEGORIES.map((category) => (
                      <option key={category.value} value={category.value}>
                        {category.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="lg:w-48">
                  <select
                    aria-label="Sort"
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    className="w-full px-4 py-3 bg-dark-800 border border-gray-600 rounded-lg text-gray-100 focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  >
                    <option value="guide">By topic</option>
                    <option value="name-asc">Name A-Z</option>
                    <option value="name-desc">Name Z-A</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 mb-8">
              {GUIDE_CATEGORIES.map((category) => {
                const style = CATEGORY_STYLE[category.value];
                const count = METRIC_GUIDE.filter((c) => c.category === category.value).length;
                return (
                  <button
                    key={category.value}
                    type="button"
                    onClick={() => setSelectedCategory(selectedCategory === category.value ? "all" : category.value)}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium ${style.color} ${
                      selectedCategory === category.value ? "ring-2 ring-offset-2 ring-offset-dark-900 ring-primary-500" : ""
                    }`}
                  >
                    {category.label} · {count}
                  </button>
                );
              })}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
              {concepts.map((concept) => (
                <ConceptCard key={concept.id} concept={concept} open={concept.id === target} />
              ))}
            </div>

            {concepts.length === 0 && (
              <div className="text-center py-12">
                <Search className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-300 mb-2">No Concepts Found</h3>
                <p className="text-gray-500">Try adjusting your search terms or category filter.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default FinancialConcepts;
