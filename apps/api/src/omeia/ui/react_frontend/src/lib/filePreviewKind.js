import { isSpreadsheetPreviewable, isTextPreviewable } from './folderBrowserUtils.js';

const CODE_EXTENSIONS = new Set([
  '.py',
  '.pyw',
  '.pyi',
  '.r',
  '.rmd',
  '.sh',
  '.bash',
  '.zsh',
  '.fish',
  '.ps1',
  '.psm1',
  '.bat',
  '.cmd',
  '.sql',
  '.ipynb',
  '.js',
  '.jsx',
  '.ts',
  '.tsx',
  '.mjs',
  '.cjs',
  '.java',
  '.c',
  '.h',
  '.hpp',
  '.cpp',
  '.cc',
  '.cxx',
  '.go',
  '.rs',
  '.rb',
  '.php',
  '.pl',
  '.pm',
  '.lua',
  '.swift',
  '.kt',
  '.kts',
  '.scala',
  '.vb',
  '.cs',
  '.fs',
  '.fsx',
  '.clj',
  '.cljs',
  '.ex',
  '.exs',
  '.erl',
  '.hrl',
  '.hs',
  '.jl',
  '.nim',
  '.zig',
  '.vue',
  '.svelte',
  '.graphql',
  '.gql',
  '.proto',
  '.tf',
  '.hcl',
  '.awk',
  '.sed',
  '.tcl',
  '.asm',
  '.s',
  '.f',
  '.f90',
  '.f95',
  '.m',
  '.mm',
  '.dockerfile',
  '.make',
  '.cmake',
  '.gradle',
  '.groovy',
  '.dart',
  '.pas',
  '.pp',
  '.v',
  '.sv',
  '.vhd',
  '.vhdl',
]);

const JSON_EXTENSIONS = new Set(['.json', '.jsonl']);
const MARKUP_EXTENSIONS = new Set(['.md', '.markdown', '.html', '.htm', '.xml']);
const PLAIN_TEXT_EXTENSIONS = new Set([
  '.txt',
  '.log',
  '.cfg',
  '.ini',
  '.toml',
  '.env',
  '.rst',
  '.tex',
  '.bib',
]);

const LANG_BY_EXT = {
  '.py': 'python',
  '.r': 'r',
  '.sh': 'bash',
  '.bash': 'bash',
  '.zsh': 'bash',
  '.sql': 'sql',
  '.js': 'javascript',
  '.jsx': 'javascript',
  '.ts': 'typescript',
  '.tsx': 'typescript',
  '.json': 'json',
  '.yaml': 'yaml',
  '.yml': 'yaml',
  '.html': 'html',
  '.xml': 'xml',
  '.md': 'markdown',
  '.java': 'java',
  '.go': 'go',
  '.rs': 'rust',
  '.rb': 'ruby',
  '.php': 'php',
  '.cpp': 'cpp',
  '.c': 'c',
  '.h': 'c',
  '.ipynb': 'json',
  '.ps1': 'powershell',
  '.psm1': 'powershell',
  '.bat': 'batch',
  '.cmd': 'batch',
  '.vue': 'vue',
  '.svelte': 'svelte',
  '.tf': 'hcl',
  '.hcl': 'hcl',
  '.proto': 'protobuf',
  '.graphql': 'graphql',
  '.gql': 'graphql',
  '.jl': 'julia',
  '.nim': 'nim',
  '.zig': 'zig',
  '.f90': 'fortran',
  '.f95': 'fortran',
  '.m': 'matlab',
  '.mm': 'objectivec',
  '.dart': 'dart',
  '.groovy': 'groovy',
  '.ex': 'elixir',
  '.exs': 'elixir',
  '.erl': 'erlang',
  '.hs': 'haskell',
  '.fs': 'fsharp',
  '.fsx': 'fsharp',
  '.clj': 'clojure',
  '.cljs': 'clojure',
  '.v': 'verilog',
  '.sv': 'verilog',
  '.vhd': 'vhdl',
  '.vhdl': 'vhdl',
};

export function inferCodeLanguage(extension, path = '') {
  const ext = (extension || '').toLowerCase();
  if (LANG_BY_EXT[ext]) return LANG_BY_EXT[ext];
  const base = (path || '').split('/').pop()?.toLowerCase() || '';
  if (base === 'dockerfile') return 'dockerfile';
  if (base === 'makefile') return 'makefile';
  return 'plaintext';
}

/** @returns {'spreadsheet'|'code'|'json'|'markup'|'text'|'document'} */
export function getFilePreviewKind(extension, path = '') {
  const ext = (extension || '').toLowerCase();
  if (isSpreadsheetPreviewable(ext)) return 'spreadsheet';
  if (CODE_EXTENSIONS.has(ext)) return 'code';
  if (JSON_EXTENSIONS.has(ext)) return 'json';
  if (MARKUP_EXTENSIONS.has(ext)) return 'markup';
  if (PLAIN_TEXT_EXTENSIONS.has(ext) || ext === '.yaml' || ext === '.yml') return 'text';
  const base = (path || '').split('/').pop()?.toLowerCase() || '';
  if (base === 'dockerfile' || base === 'makefile' || base === 'gemfile' || base === 'rakefile') {
    return 'code';
  }
  if (isTextPreviewable(ext)) return 'code';
  return 'document';
}

export function shouldFetchRawFile(kind) {
  return kind === 'code' || kind === 'json' || kind === 'text' || kind === 'markup';
}
