import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = path.resolve(__dirname, '../../../../')

/** Mirror configs/.env Firebase keys into VITE_* when react_frontend/.env.local omits them. */
function loadSharedFirebaseEnv() {
  const envPath = path.join(REPO_ROOT, 'configs', '.env')
  if (!fs.existsSync(envPath)) return

  const mappings = [
    ['FIREBASE_WEB_API_KEY', 'VITE_FIREBASE_API_KEY'],
    ['FIREBASE_AUTH_DOMAIN', 'VITE_FIREBASE_AUTH_DOMAIN'],
    ['FIREBASE_PROJECT_ID', 'VITE_FIREBASE_PROJECT_ID'],
    ['FIREBASE_STORAGE_BUCKET', 'VITE_FIREBASE_STORAGE_BUCKET'],
    ['FIREBASE_MESSAGING_SENDER_ID', 'VITE_FIREBASE_MESSAGING_SENDER_ID'],
    ['FIREBASE_WEB_APP_ID', 'VITE_FIREBASE_APP_ID'],
    ['FIREBASE_MEASUREMENT_ID', 'VITE_FIREBASE_MEASUREMENT_ID'],
  ]

  for (const line of fs.readFileSync(envPath, 'utf8').split('\n')) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const eq = trimmed.indexOf('=')
    if (eq < 1) continue
    const key = trimmed.slice(0, eq).trim()
    const value = trimmed.slice(eq + 1).trim().replace(/^["']|["']$/g, '')
    for (const [from, to] of mappings) {
      if (key === from && value && !process.env[to]) {
        process.env[to] = value
      }
    }
  }
}

loadSharedFirebaseEnv()
const DATABASE_ROOT_ENV = process.env.DATABASE_ROOT?.trim()
const EXTERNAL_DATABASE_ROOT = path.resolve(REPO_ROOT, '..', 'OMEIA-database')
const LEGACY_DATABASE_ROOT = path.join(REPO_ROOT, 'database')
function resolveDatabaseRoot() {
  const candidates = [
    DATABASE_ROOT_ENV ? path.resolve(DATABASE_ROOT_ENV) : null,
    EXTERNAL_DATABASE_ROOT,
    LEGACY_DATABASE_ROOT,
  ].filter(Boolean)
  for (const root of candidates) {
    if (fs.existsSync(path.join(root, 'WET_LAB'))) return root
  }
  for (const root of candidates) {
    if (fs.existsSync(root)) return root
  }
  return LEGACY_DATABASE_ROOT
}
const DATABASE_ROOT = resolveDatabaseRoot()
const DATABASE_PROJECTS = path.join(DATABASE_ROOT, 'projects')
const LEGACY_PROJECTS = path.join(REPO_ROOT, 'projects')
const PROJECTS_ROOT = fs.existsSync(DATABASE_PROJECTS)
  ? DATABASE_PROJECTS
  : LEGACY_PROJECTS

const MIME = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
  '.svg': 'image/svg+xml',
  '.tif': 'image/tiff',
  '.tiff': 'image/tiff',
  '.pdf': 'application/pdf',
  '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  '.ppt': 'application/vnd.ms-powerpoint',
  '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  '.doc': 'application/msword',
  '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  '.xls': 'application/vnd.ms-excel',
}

/** Serve /database-static/* from the lab database folder (dev — open original PDFs/DOCX). */
function databaseStaticPlugin() {
  return {
    name: 'database-static',
    configureServer(server) {
      server.middlewares.use('/database-static', (req, res, next) => {
        try {
          const urlPath = decodeURIComponent((req.url || '').split('?')[0])
          const rel = urlPath.replace(/^\/+/, '')
          if (!rel) {
            res.statusCode = 404
            return res.end('Not found')
          }
          const filePath = path.normalize(path.join(DATABASE_ROOT, rel))
          if (!filePath.startsWith(DATABASE_ROOT)) {
            res.statusCode = 403
            return res.end('Forbidden')
          }
          if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
            res.statusCode = 404
            return res.end(`Not found: ${rel}`)
          }
          const ext = path.extname(filePath).toLowerCase()
          res.setHeader('Content-Type', MIME[ext] || 'application/octet-stream')
          res.setHeader('Cache-Control', 'no-cache')
          fs.createReadStream(filePath).pipe(res)
        } catch (err) {
          next(err)
        }
      })
    },
  }
}

/** Serve /projects-static/* directly from the projects folder (dev — no API restart needed). */
function projectsStaticPlugin() {
  return {
    name: 'projects-static',
    configureServer(server) {
      server.middlewares.use('/projects-static', (req, res, next) => {
        try {
          const urlPath = decodeURIComponent((req.url || '').split('?')[0])
          const rel = urlPath.replace(/^\/+/, '')
          if (!rel) {
            res.statusCode = 404
            return res.end('Not found')
          }
          const filePath = path.normalize(path.join(PROJECTS_ROOT, rel))
          if (!filePath.startsWith(PROJECTS_ROOT)) {
            res.statusCode = 403
            return res.end('Forbidden')
          }
          if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
            res.statusCode = 404
            return res.end(`Not found: ${rel}`)
          }
          const ext = path.extname(filePath).toLowerCase()
          res.setHeader('Content-Type', MIME[ext] || 'application/octet-stream')
          res.setHeader('Cache-Control', 'no-cache')
          fs.createReadStream(filePath).pipe(res)
        } catch (err) {
          next(err)
        }
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), databaseStaticPlugin(), projectsStaticPlugin()],
  server: {
    host: true,
    fs: {
      allow: [DATABASE_ROOT, PROJECTS_ROOT, path.resolve(__dirname, '..')],
    },
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/health': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/stats': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/ask': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/projects': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/notebook': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/decisions': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/wiki': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/tasks': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/team': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/checklists': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/folders': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/datasets': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/pipeline_runs': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/auto_logs': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/platform': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/install_guide': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/lumi_job': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/parse_log': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/run_checker': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/ingest-document': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/gap-analysis': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/features': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/clinical': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/analysis-runs': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/ai-models': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/infrastructure': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/publications': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/csc-media': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/projects-static': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/database-static': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
})
