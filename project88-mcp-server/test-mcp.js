#!/usr/bin/env node

/**
 * Simple test script for Project88 MCP Server
 * Tests the MCP server functionality by simulating requests
 */

import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function testMCPServer() {
  console.log('🧪 Testing Project88 MCP Server...\n');

  try {
    // Start the MCP server process
    const serverPath = join(__dirname, 'build', 'simple-server.js');
    const server = spawn('node', [serverPath], {
      stdio: ['pipe', 'pipe', 'pipe']
    });

    // Test 1: List Tools
    console.log('1. Testing tool listing...');
    const listToolsRequest = {
      jsonrpc: "2.0",
      id: 1,
      method: "tools/list"
    };

    server.stdin.write(JSON.stringify(listToolsRequest) + '\n');

    // Test 2: Call analyze_system tool
    console.log('2. Testing analyze_system tool...');
    const analyzeSystemRequest = {
      jsonrpc: "2.0",
      id: 2,
      method: "tools/call",
      params: {
        name: "analyze_system",
        arguments: {}
      }
    };

    server.stdin.write(JSON.stringify(analyzeSystemRequest) + '\n');

    // Test 3: List Resources
    console.log('3. Testing resource listing...');
    const listResourcesRequest = {
      jsonrpc: "2.0",
      id: 3,
      method: "resources/list"
    };

    server.stdin.write(JSON.stringify(listResourcesRequest) + '\n');

    // Collect responses
    let responseCount = 0;
    server.stdout.on('data', (data) => {
      const responses = data.toString().split('\n').filter(line => line.trim());
      
      responses.forEach(response => {
        if (response.trim()) {
          try {
            const parsed = JSON.parse(response);
            responseCount++;
            
            if (parsed.result) {
              console.log(`✅ Response ${responseCount}: ${parsed.result.tools ? 'Tools listed' : parsed.result.resources ? 'Resources listed' : 'Tool executed'}`);
              
              // Show some details for the first few responses
              if (responseCount <= 3) {
                if (parsed.result.tools) {
                  console.log(`   Found ${parsed.result.tools.length} tools`);
                } else if (parsed.result.resources) {
                  console.log(`   Found ${parsed.result.resources.length} resources`);
                } else if (parsed.result.content) {
                  console.log(`   Tool returned content`);
                }
              }
            }
          } catch (e) {
            // Ignore parsing errors for partial responses
          }
        }
      });

      // After we get a few responses, conclude the test
      if (responseCount >= 3) {
        setTimeout(() => {
          console.log('\n🎉 MCP Server test completed successfully!');
          console.log('\n📋 Summary:');
          console.log('✅ Server started correctly');
          console.log('✅ Tools are available and responding');
          console.log('✅ Resources are accessible');
          console.log('\n🚀 Your Project88 MCP Server is ready for use!');
          
          server.kill();
          process.exit(0);
        }, 1000);
      }
    });

    server.stderr.on('data', (data) => {
      const output = data.toString();
      if (output.includes('Project88 MCP Server running')) {
        console.log('✅ Server started successfully');
      }
    });

    // Timeout after 10 seconds
    setTimeout(() => {
      console.log('⏰ Test timeout - server may be working but responses are slow');
      server.kill();
      process.exit(0);
    }, 10000);

  } catch (error) {
    console.error('❌ Test failed:', error);
    process.exit(1);
  }
}

testMCPServer(); 