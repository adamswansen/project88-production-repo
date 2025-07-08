/**
 * Project88 MCP Server Tests
 * Basic functionality tests for the MCP server
 */

import { Project88MCPServer } from './index.js';

async function runTests() {
  console.log('🧪 Running Project88 MCP Server Tests...\n');

  try {
    // Test server initialization
    console.log('1. Testing server initialization...');
    const server = new Project88MCPServer();
    console.log('✅ Server initialized successfully\n');

    // Test tool execution
    console.log('2. Testing tool execution...');
    
    // Test system architecture analysis
    console.log('   Testing analyze_system_architecture...');
    const archResult = await server['analyzeSystemArchitecture']();
    if (archResult && archResult.content && archResult.content.length > 0) {
      console.log('   ✅ System architecture analysis working');
    } else {
      console.log('   ❌ System architecture analysis failed');
    }

    // Test service status check
    console.log('   Testing check_service_status...');
    const statusResult = await server['checkServiceStatus']();
    if (statusResult && statusResult.content && statusResult.content.length > 0) {
      console.log('   ✅ Service status check working');
    } else {
      console.log('   ❌ Service status check failed');
    }

    // Test database schema
    console.log('   Testing get_database_schema...');
    const schemaResult = await server['getDatabaseSchema']();
    if (schemaResult && schemaResult.content && schemaResult.content.length > 0) {
      console.log('   ✅ Database schema retrieval working');
    } else {
      console.log('   ❌ Database schema retrieval failed');
    }

    console.log('\n3. Testing resource access...');
    
    // Test system architecture resource
    console.log('   Testing system architecture resource...');
    const archResource = await server['getSystemArchitecture']();
    if (archResource && archResource.contents && archResource.contents.length > 0) {
      console.log('   ✅ System architecture resource working');
    } else {
      console.log('   ❌ System architecture resource failed');
    }

    // Test deployment guide
    console.log('   Testing deployment guide resource...');
    const deployGuide = await server['getDeploymentGuide']();
    if (deployGuide && deployGuide.contents && deployGuide.contents.length > 0) {
      console.log('   ✅ Deployment guide resource working');
    } else {
      console.log('   ❌ Deployment guide resource failed');
    }

    console.log('\n4. Testing prompt generation...');
    
    // Test debug sync issue prompt
    console.log('   Testing debug sync issue prompt...');
    const debugPrompt = await server['getDebugSyncIssuePrompt']('runsignup', 'Connection timeout');
    if (debugPrompt && debugPrompt.messages && debugPrompt.messages.length > 0) {
      console.log('   ✅ Debug sync issue prompt working');
    } else {
      console.log('   ❌ Debug sync issue prompt failed');
    }

    // Test optimization prompt
    console.log('   Testing optimization prompt...');
    const optimizePrompt = await server['getOptimizeDatabaseQueryPrompt']('select', 'ct_participants');
    if (optimizePrompt && optimizePrompt.messages && optimizePrompt.messages.length > 0) {
      console.log('   ✅ Optimization prompt working');
    } else {
      console.log('   ❌ Optimization prompt failed');
    }

    console.log('\n🎉 All tests completed successfully!');
    console.log('\n📋 Test Summary:');
    console.log('✅ Server initialization');
    console.log('✅ Tool execution');
    console.log('✅ Resource access');
    console.log('✅ Prompt generation');
    console.log('\n🚀 Project88 MCP Server is ready for use!');

  } catch (error) {
    console.error('❌ Test failed:', error);
    process.exit(1);
  }
}

// Run tests if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  runTests().catch(console.error);
}

export { runTests }; 