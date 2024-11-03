# Search Term Analyzer

Part of a comprehensive agentic framework suite designed to optimize Google Ads Quality Score across its three core components: Expected CTR, Ad Relevance, and Landing Page Experience. This specific tool focuses on the Ad Relevance component, providing intelligent search term analysis and actionable optimization recommendations.

## 🎯 Purpose

The Search Term Analyzer specializes in improving Ad Relevance scores by analyzing search terms and their performance patterns. Despite its name, Ad Relevance is less about ad copy optimization (which falls under Expected CTR) and more about ensuring your keyword targeting strategy aligns with user search intent and campaign goals.

## 💡 What Makes This Different

Unlike traditional search term analysis tools that focus solely on linguistic patterns or basic performance metrics, this framework:

1. **Integrates Business Intelligence**: Uses actual Google Ads KPIs (cost, conversions, CPA, revenue, ROAS, AOV, CVR) alongside linguistic analysis to make decisions
2. **Multi-level Decision Making**: Automatically determines not just whether to act on a search term, but exactly how (do nothing, add as keyword, or add as negative at the appropriate level)
3. **Account-wide Intelligence**: Makes decisions with full awareness of account structure and cross-campaign impacts
4. **Strategic Grouping**: Doesn't just analyze terms in isolation - identifies patterns across terms that might not be visible when looking at individual performance
5. **Automated Decision Chain**: Uses the output of one analysis technique as input for the next, creating a sophisticated decision tree

### Strategic Framework Position
- **Expected CTR Optimization**: Handled by companion framework (ad copy optimization)
- **Ad Relevance**: Primary focus of this tool
- **Landing Page Experience**: Handled by companion framework (landing page optimization)

## 🧠 Core Capabilities

The analyzer employs a sophisticated decision-making pipeline to process search terms individually and in strategic groups, outputting actionable targeting recommendations:

### Analysis Outputs
- Do Nothing (term performs within acceptable parameters)
- Add as Exact Match Keyword (high potential terms)
- Add as Negative Keyword with intelligent level selection:
  - Ad Group Level
  - Campaign Level
  - Account Level

- **Performance Thresholds**
  - Customizable KPI thresholds
  - Historical performance benchmarking
  - Statistical significance requirements
  - Risk-adjusted decision making
  
### Advanced Analysis Pipeline
### Analysis Chain Flow
The system processes search terms through sequential analysis stages:
1. **Initial Filtering**: Basic performance metrics and linguistic patterns
2. **Deep Analysis**: Results from initial filtering feed into more sophisticated analysis
3. **Group Pattern Detection**: Individual term analysis results are grouped to detect broader patterns
4. **Account Impact Assessment**: Final recommendations are validated against account-wide implications

- **Linguistic Processing**
  - Rule-based analysis with customizable rulesets
  - Fuzzy matching for variant detection
  - N-gram analysis for pattern recognition
  - Semantic similarity scoring
  - Natural Language Processing (NLP) integration
  - Confidence-based filtering

- **Performance Analysis**
  - Cost and conversion analysis
  - ROAS and CPA optimization
  - Historical performance trending
  - Competitive metric analysis
  - Statistical significance testing

- **Strategic Grouping**
  - Hierarchical clustering
  - Intent-based categorization
  - Cross-campaign pattern recognition
  - Account-wide impact assessment

### Technical Features

- **Distributed Processing**
  - Scalable worker architecture
  - Batch processing support
  - Fault tolerance and recovery
  - Real-time worker health monitoring

- **Performance Optimizations**
  - Intelligent caching system
  - Configurable batch sizes
  - Resource-aware processing
  - Optimized data structures

- **RESTful API Integration**
  - FastAPI-based endpoints
  - Real-time analysis capabilities
  - Batch processing endpoints
  - Comprehensive API documentation

- **Monitoring and Metrics**
  - Detailed performance metrics
  - Processing statistics
  - Worker health monitoring
  - Custom metric support

## 🛠️ Implementation Architecture

1. **Input Processing Layer**
   - Search term data ingestion
   - Performance metric integration
   - Historical data processing
   - Account structure awareness

2. **Analysis Layer**
   - Multi-stage analysis pipeline
   - Parallel processing capabilities
   - Configurable analysis rules
   - Machine learning integration

3. **Decision Layer**
   - Recommendation generation
   - Confidence scoring
   - Impact prediction
   - Action prioritization

4. **Output Layer**
   - Structured recommendations
   - Performance forecasting
   - Implementation guidance
   - Audit trail generation

- **Distributed Processing**
  - Scalable worker architecture
  - Batch processing support
  - Fault tolerance and recovery
  - Real-time worker health monitoring

- **Performance Optimizations**
  - Intelligent caching system
  - Configurable batch sizes
  - Resource-aware processing
  - Optimized data structures

- **RESTful API Integration**
  - FastAPI-based endpoints
  - Real-time analysis capabilities
  - Batch processing endpoints
  - Comprehensive API documentation

- **Monitoring and Metrics**
  - Detailed performance metrics
  - Processing statistics
  - Worker health monitoring
  - Custom metric support

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/search-term-analyzer.git
cd search-term-analyzer

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

## 📋 Requirements

- Python 3.9+
- Dependencies listed in pyproject.toml
- Optional: Redis for distributed caching
- Optional: Dask for distributed processing

## 🔧 Configuration

Configuration is managed through JSON files and environment variables. Key configuration areas include:

- Processing settings (batch size, timeouts, etc.)
- Analysis parameters (thresholds, weights)
- Caching behavior
- Monitoring settings
- Distributed processing options

Example configuration:
```json
{
    "processing": {
        "batch_size": 32,
        "max_workers": 4,
        "timeout": 30.0
    },
    "cache": {
        "enabled": true,
        "max_size": 10000,
        "ttl_seconds": 3600
    }
}
```

## 🚦 Usage

### Basic Usage

```python
from search_term_analyzer.pipeline import SearchTermAnalyzer
from search_term_analyzer.core.config import PipelineConfig

# Initialize analyzer
config = PipelineConfig.load('config.json')
analyzer = SearchTermAnalyzer(config)

# Analyze single term
result = await analyzer.analyze_term("example search term")

# Process batch
results = await analyzer.process_batch(terms_list)
```

### Distributed Processing

```python
from search_term_analyzer.distributed import AnalysisClient

# Initialize client
client = AnalysisClient(config)
await client.connect("scheduler_address")

# Submit batch for processing
batch_id = await client.submit_batch(terms_list)

# Get results
results = await client.get_results(batch_id)
```

## 📊 Monitoring

The system provides comprehensive monitoring capabilities:

- Processing metrics (throughput, latency)
- Quality metrics (confidence scores, accuracy)
- System metrics (CPU, memory usage)
- Worker health status
- Cache performance

## 🧪 Testing

```bash
# Run test suite
pytest

# Run with coverage
pytest --cov=search_term_analyzer tests/
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔍 Project Structure

```
search_term_analyzer/
├── src/
│   └── search_term_analyzer/
│       ├── api/          # FastAPI endpoints
│       ├── core/         # Core functionality
│       ├── distributed/  # Distributed processing
│       ├── models/       # Data models
│       ├── pipeline/     # Analysis pipeline
│       └── utils/        # Utility functions
├── tests/                # Test suite
├── docs/                 # Documentation
└── examples/            # Usage examples
```

## ✨ Roadmap

- [ ] Machine learning model integration
- [ ] Real-time analysis streaming
- [ ] Advanced visualization dashboard
- [ ] Multi-language support
- [ ] Custom plugin system

## 📫 Contact

Your Name - bjorndavidhansen@gmail.com
Project Link: [https://github.com/bjorndavidhansen/search_term_analyzer](https://github.com/bjorndavidhansen/search_term_analyzer)