import { ArrowLeft, Globe } from "lucide-react";
import { useState } from "react";

import LoadingSpinner from "../../shared/ui/Spinner";
import { usePublicWatchlist, usePublicWatchlists } from "./queries";
import WatchlistContent from "./WatchlistContent";

// Other people's public watchlists, read only
const PublicWatchlists = ({ currentUserId }) => {
  const [open, setOpen] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const lists = usePublicWatchlists(open);
  const selected = usePublicWatchlist(selectedId);
  const others = (lists.data || []).filter((list) => list.user_id !== currentUserId);

  return (
    <section className="mt-10">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-100 flex items-center gap-2">
          <Globe size={18} className="text-primary-400" />
          Public watchlists
        </h2>
        <button
          type="button"
          className="btn-secondary text-sm"
          onClick={() => {
            setOpen(!open);
            setSelectedId(null);
          }}
        >
          {open ? "Hide" : "Browse"}
        </button>
      </div>
      {open &&
        (selectedId !== null ? (
          <div>
            <button
              type="button"
              onClick={() => setSelectedId(null)}
              className="mb-4 flex items-center gap-2 text-sm text-gray-400 hover:text-gray-100"
            >
              <ArrowLeft size={16} /> All public watchlists
            </button>
            {selected.isPending ? (
              <LoadingSpinner centered />
            ) : selected.data ? (
              <>
                <h3 className="text-xl font-semibold text-gray-100">{selected.data.name}</h3>
                {selected.data.description && (
                  <p className="text-sm text-gray-400 mb-4">{selected.data.description}</p>
                )}
                <WatchlistContent watchlist={selected.data} readOnly />
              </>
            ) : (
              <p className="text-sm text-gray-400">This watchlist is no longer public.</p>
            )}
          </div>
        ) : lists.isPending ? (
          <LoadingSpinner centered />
        ) : others.length === 0 ? (
          <p className="text-sm text-gray-400">No one else has shared a watchlist yet.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {others.map((list) => (
              <button
                type="button"
                key={list.id}
                onClick={() => setSelectedId(list.id)}
                className="text-left p-6 bg-dark-800 rounded-xl hover:bg-dark-700 border border-dark-700 transition-colors"
              >
                <h3 className="text-lg font-semibold text-gray-100 truncate">{list.name}</h3>
                {list.description && (
                  <p className="text-sm text-gray-400 line-clamp-2">{list.description}</p>
                )}
                <p className="mt-2 text-xs text-gray-500">{list.item_count ?? 0} symbols</p>
              </button>
            ))}
          </div>
        ))}
    </section>
  );
};

export default PublicWatchlists;
