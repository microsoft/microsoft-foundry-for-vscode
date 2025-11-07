# Multi-Agent Visualization in Visual Studio Code

By using the Azure AI Foundry for Visual Studio Code extension, you can visualize the interactions between agents and how they collaborate to achieve your desired outcome.

## Python

Enable visualization in your workflows by adding the following code snippet:

```Python
from agent_framework.observability import setup_observability
setup_observability(vs_code_extension_port=4319)
```

To monitor and visualize your multi-agent workflow execution in real time

1. Open the command palette (Ctrl+Shift+P).
2. Run this command: `>Azure AI Foundry: Open Visualizer for Hosted Agents`. A new tab opens in VS Code to display the execution graph. The visualization updates itself automatically as your workflow progresses, to show the flow between agents and their interactions.
3. Now you can run your Python application, and the multi-agent visualization will be available in the VS Code tab.

## .NET

Add the following reference to your csproj file:

```xml
<ItemGroup>
    <PackageReference Include="OpenTelemetry" Version="1.12.0" />
    <PackageReference Include="OpenTelemetry.Exporter.Console" Version="1.12.0" />
    <PackageReference Include="OpenTelemetry.Exporter.OpenTelemetryProtocol" Version="1.12.0" />
    <PackageReference Include="System.Diagnostics.DiagnosticSource" Version="9.0.10" />
</ItemGroup>
```

Update your program to include the following code snippet:

```CSharp
using System.Diagnostics;
using OpenTelemetry;
using OpenTelemetry.Logs;
using OpenTelemetry.Metrics;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var otlpEndpoint =
    Environment.GetEnvironmentVariable("OTLP_ENDPOINT") ?? "http://localhost:4319";

var resourceBuilder = OpenTelemetry
    .Resources.ResourceBuilder.CreateDefault()
    .AddService("WorkflowSample");

var s_tracerProvider = OpenTelemetry
    .Sdk.CreateTracerProviderBuilder()
    .SetResourceBuilder(resourceBuilder)
    .AddSource("Microsoft.Agents.AI.Workflows*")
    .AddOtlpExporter(options =>
    {
        options.Endpoint = new Uri(otlpEndpoint);
        options.Protocol = OpenTelemetry.Exporter.OtlpExportProtocol.Grpc;
    })
    .Build();

Console.WriteLine($"OpenTelemetry configured. OTLP endpoint: {otlpEndpoint}");
```

To monitor and visualize your multi-agent workflow execution in real time

1. Open the command palette (Ctrl+Shift+P).
2. Run this command: `>Azure AI Foundry: Open Visualizer for Hosted Agents`. A new tab opens in VS Code to display the execution graph. The visualization updates itself automatically as your workflow progresses, to show the flow between agents and their interactions.
3. Now you can run your .NET application, and the multi-agent visualization will be available in the VS Code tab.
