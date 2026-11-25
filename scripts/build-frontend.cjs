const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const output = path.join(root, 'dist', 'frontend');
const files = ['index.html', 'nav.js', 'api-client.js', 'ui-dialogs.js'];
const directories = [
  'Dashboard',
  'Expense',
  'Img',
  'Inventory',
  'Login Page',
  'POS',
  'Settings',
  'Transactions'
];

fs.rmSync(output, { recursive: true, force: true });
fs.mkdirSync(output, { recursive: true });

for (const file of files) {
  fs.copyFileSync(path.join(root, file), path.join(output, file));
}

for (const directory of directories) {
  fs.cpSync(path.join(root, directory), path.join(output, directory), {
    recursive: true
  });
}
