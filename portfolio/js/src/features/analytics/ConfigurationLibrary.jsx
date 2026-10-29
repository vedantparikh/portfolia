import { BookTemplate, Copy, Plus, TrendingUp } from "lucide-react";
import { toast } from "react-hot-toast";

import { apiErrorMessage } from "../../shared/api/client";
import { statisticalIndicatorsAPI } from "../../shared/api/indicators";
import { formatRatio } from "../../utils/formatters.jsx";
import {
  invalidateIndicatorConfigurations,
  useConfigurationStatistics,
  useIndicatorTemplates,
  usePopularConfigurations,
} from "./queries";

const Chips = ({ indicators = [] }) => (
  <div className="flex flex-wrap gap-1 mt-2">
    {indicators.map((indicator, i) => (
      <span
        key={indicator.id ?? `${indicator.indicator_name}-${i}`}
        className="px-2 py-0.5 bg-primary-600/20 text-primary-400 text-xs rounded-full"
      >
        {indicator.display_name || indicator.indicator_name}
      </span>
    ))}
  </div>
);

// Starting points for your own sets: built-in templates, popular public sets, and your counts
const ConfigurationLibrary = () => {
  const { data: templates = {} } = useIndicatorTemplates();
  const { data: popular = [] } = usePopularConfigurations();
  const { data: stats } = useConfigurationStatistics();

  const copy = async (action, message) => {
    try {
      await action();
      invalidateIndicatorConfigurations();
      toast.success(message);
    } catch (error) {
      toast.error(apiErrorMessage(error, "Could not copy that set"));
    }
  };

  return (
    <div className="space-y-6 pt-4 border-t border-dark-700">
      {stats && stats.total_configurations > 0 && (
        <p className="text-sm text-gray-400">
          You have {stats.total_configurations} sets ({stats.public_configurations} public),{" "}
          {formatRatio(stats.average_indicators_per_config, 1)} indicators each on average
          {stats.most_used_indicators?.length > 0 &&
            `; most used: ${stats.most_used_indicators
              .slice(0, 3)
              .map(([name]) => name)
              .join(", ")}`}
          .
        </p>
      )}

      <section>
        <h4 className="font-medium text-gray-100 flex items-center gap-2 mb-3">
          <BookTemplate size={16} className="text-primary-400" /> Templates
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {Object.entries(templates).map(([key, template]) => (
            <div key={key} className="p-4 bg-dark-800 rounded-lg">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-medium text-gray-100">{template.name}</p>
                  <p className="text-xs text-gray-500 capitalize">{template.difficulty_level}</p>
                </div>
                <button
                  type="button"
                  className="btn-outline text-xs flex items-center gap-1"
                  onClick={() =>
                    copy(
                      () => statisticalIndicatorsAPI.createFromTemplate(key),
                      `"${template.name}" added to your sets`,
                    )
                  }
                >
                  <Plus size={12} /> Use
                </button>
              </div>
              <p className="text-sm text-gray-400 mt-1">{template.description}</p>
              <Chips indicators={template.indicators} />
            </div>
          ))}
        </div>
      </section>

      {popular.length > 0 && (
        <section>
          <h4 className="font-medium text-gray-100 flex items-center gap-2 mb-3">
            <TrendingUp size={16} className="text-primary-400" /> Popular public sets
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {popular.map((config) => (
              <div key={config.id} className="p-4 bg-dark-800 rounded-lg">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-medium text-gray-100">{config.name}</p>
                    <p className="text-xs text-gray-500">Used {config.usage_count ?? 0} times</p>
                  </div>
                  <button
                    type="button"
                    className="btn-outline text-xs flex items-center gap-1"
                    onClick={() =>
                      copy(
                        () =>
                          statisticalIndicatorsAPI.duplicateConfiguration(
                            config.id,
                            `${config.name} (Copy)`,
                          ),
                        `"${config.name}" copied to your sets`,
                      )
                    }
                  >
                    <Copy size={12} /> Copy
                  </button>
                </div>
                {config.description && <p className="text-sm text-gray-400 mt-1">{config.description}</p>}
                <Chips indicators={config.indicators} />
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
};

export default ConfigurationLibrary;
