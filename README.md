# green-go

AI Agent that controls your at-home smart devices to optimize costs and marginal emissions rates (leveraging Enode and Watttime API)

## Overview

green-go is an intelligent energy management system that automatically optimizes your home's energy consumption by coordinating with your smart devices. By leveraging the Enode API and real-time marginal emissions data, the system analyzes energy costs and grid carbon intensity to make intelligent decisions that reduce costs and minimize environmental impact.

## Features

- **Smart Device Integration**: Connect and control multiple smart devices across your home
- **Real-time Energy Monitoring**: Track energy consumption patterns in real-time
- **Automated Optimization**: AI-driven algorithms automatically adjust device operations for maximum efficiency
- **Cost Reduction**: Minimize energy bills through intelligent scheduling and optimization
- **Environmental Impact**: Reduce your carbon footprint by optimizing energy usage
- **Enode API Integration**: Seamlessly connect with Enode's comprehensive energy management platform
- **Marginal Emissions Rate Integration**: Incorporates real-time marginal operational emissions rates from WattTime.org to minimize grid carbon intensity

## Architecture

The system monitors connected smart devices and applies machine learning algorithms to optimize energy consumption based on usage patterns, time of day, and energy pricing.

## User Interface

![green-go Dashboard1](ui_wireframe1.png)
![green-go Dashboard2](ui_wireframe2.png)

The intuitive dashboard provides real-time insights into your energy consumption, device status, and optimization recommendations.

[View Interactive Mockup](https://rawcdn.githack.com/vsocrates/green-go/fdc3446cbcea2784e2044a4106f06b598a30bbad/green-go-demo.html)

## Getting Started

### Prerequisites

- Python 3.8+
- Enode API credentials
- Smart home devices compatible with Enode

### Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure your Enode API credentials
4. Connect your smart devices through the Enode platform

## Usage

Start the agent with your configuration:

```bash
python green_go.py --config config.yaml
```

## Configuration

Configure your devices and optimization preferences in `config.yaml`:

```yaml
enode_api_key: your_api_key
optimization_mode: aggressive
devices:
  - type: thermostat
  - type: ev_charger
  - type: water_heater
```

## API Integration

green-go uses the Enode API to communicate with smart devices. Refer to the [Enode Documentation](https://developers.enode.com/api/reference) for detailed API specifications.

For marginal emissions data integration, we use the [WattTime Python Client](https://github.com/WattTime/watttime-python-client).

## Future Direction

- **Real-time Pricing Integration**: Incorporate real-time pricing information from utilities to optimize device scheduling based on dynamic energy rates
- **Enhanced DER Control**: Add additional Distributed Energy Resource (DER) control capabilities using tools such as [DER API](https://derapi.com/)
- **Utility Demand Response Integration**: Link to utility demand response programs to participate in grid optimization initiatives and earn incentives
- **User Notifications**: Implement smart notifications for instances where users do not have smart appliances, providing actionable recommendations
- **Multi-Agent Optimization**: Enable connectivity between individual agents to neighborhood-level and regional agents to further optimize emissions and energy use across wider areas

## License

MIT License - See LICENSE file for details
