import { Component } from "react";
import { Link } from "react-router";

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidUpdate(prevProps) {
    if (prevProps.resetKey !== this.props.resetKey && this.state.error) {
      this.setState({ error: null });
    }
  }

  render() {
    if (!this.state.error) {
      return this.props.children;
    }
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center p-6">
        <div className="text-center max-w-md">
          <h1 className="text-xl font-semibold text-gray-100">
            This page failed to load
          </h1>
          <p className="text-sm text-gray-400 mt-2">
            The rest of the app is still available.
          </p>
          <Link to="/dashboard" className="inline-block mt-4 text-primary-400">
            Back to dashboard
          </Link>
        </div>
      </div>
    );
  }
}

export default ErrorBoundary;
