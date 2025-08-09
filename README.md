# Spring Input Booleans

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

A Home Assistant custom integration that automatically reverses changes to input boolean entities. When an input boolean is turned on, it will immediately be turned off, and when it's turned off, it will immediately be turned on - like a spring-loaded switch that always returns to its previous position.

## Features

- 🔄 Automatically reverses any state change to input_boolean entities
- ⚡ Real-time response to state changes
- 🎯 Works with all input_boolean entities in your Home Assistant instance
- 📝 Detailed logging for debugging
- 🔧 Easy installation via HACS

## Installation

### Via HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/lucasschonrock/hacs-spring-input-booleans`
6. Select "Integration" as the category
7. Click "Add"
8. Find "Spring Input Booleans" in the integration list and install it
9. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/lucasschonrock/hacs-spring-input-booleans/releases)
2. Extract the contents
3. Copy the `custom_components/spring_input_booleans` folder to your Home Assistant `custom_components` directory
4. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services → Integrations
2. Click "Add Integration"
3. Search for "Spring Input Booleans"
4. Click to add the integration
5. Follow the configuration flow

## Usage

Once installed and configured, the integration will automatically monitor all input_boolean entities in your Home Assistant instance. Any time an input boolean's state changes:

- If turned **ON** → Immediately turned **OFF**
- If turned **OFF** → Immediately turned **ON**

This creates a "spring-loaded" effect where the input booleans always snap back to their previous state.

### Example Scenarios

- **Testing automations**: Use this to test how your automations handle rapid state changes
- **Demonstration purposes**: Show the spring-like behavior for educational purposes
- **Preventing accidental changes**: Ensure certain input booleans can't be permanently changed

## Logging

The integration provides detailed logging. To enable debug logging, add this to your `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.spring_input_booleans: debug
```

## Troubleshooting

### Integration doesn't seem to work

1. Check that the integration is properly installed and enabled
2. Verify that you have input_boolean entities in your Home Assistant
3. Check the logs for any error messages
4. Ensure Home Assistant has restarted after installation

### Performance concerns

This integration listens to all state change events and filters for input_boolean entities. In most Home Assistant installations, this should have minimal performance impact. However, if you have a very large number of state changes, you may want to monitor system performance.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

If you encounter any issues or have questions, please [open an issue](https://github.com/lucasschonrock/hacs-spring-input-booleans/issues) on GitHub.
