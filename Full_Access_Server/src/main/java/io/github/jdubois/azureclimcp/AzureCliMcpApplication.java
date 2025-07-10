package io.github.jdubois.azureclimcp;

import org.springframework.ai.tool.ToolCallbackProvider;
import org.springframework.ai.tool.method.MethodToolCallbackProvider;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

@SpringBootApplication
public class AzureCliMcpApplication {

	public static void main(String[] args) {
		SpringApplication.run(AzureCliMcpApplication.class, args);
	}

	@Bean
	public ToolCallbackProvider mcpTool(AzureCliService azureCliService) {
		return MethodToolCallbackProvider.builder().toolObjects(azureCliService).build();
	}

}
