#!/usr/bin/env node

import { Command } from 'commander';
import axios from 'axios';
import chalk from 'chalk'; // I'll use simple colors since I can't guarantee chalk is installed yet

const program = new Command();
const BACKEND_URL = 'http://localhost:8000';

program
  .name('skills')
  .description('Project Rain Skill Manager')
  .version('0.1.0');

program
  .command('add')
  .description('Install a new skill from a Git repository')
  .argument('<url>', 'Git repository URL')
  .option('-s, --skill <name>', 'Specific skill name to install')
  .action(async (url, options) => {
    console.log(`\n🌧️  ${(chalk?.cyan || String)('Rain Skill Manager')}`);
    console.log(`📦 Installing skill from: ${url}`);
    if (options.skill) {
      console.log(`🎯 Targeted skill: ${options.skill}`);
    }

    try {
      const response = await axios.post(`${BACKEND_URL}/v1/skills/install`, {
        git_url: url,
        skill_name: options.skill || null
      });

      console.log(`\n✅ ${(chalk?.green || String)('Success!')} Skill installed: ${response.data.name}`);
      console.log(`🌐 Version: ${response.data.version}`);
    } catch (error) {
      console.error(`\n❌ ${(chalk?.red || String)('Installation failed:')}`);
      if (error.response) {
        console.error(`   Error: ${error.response.data.error?.message || error.response.data.detail || 'Internal Server Error'}`);
      } else {
        console.error(`   Error: ${error.message}`);
      }
      process.exit(1);
    }
  });

program
  .command('list')
  .description('List all installed skills')
  .action(async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/v1/models`); // We should use a skills list endpoint
      console.log('\n🛠️  Installed Skills:');
      // Logic to list skills
    } catch (error) {
      console.error('Failed to list skills');
    }
  });

program.parse();
