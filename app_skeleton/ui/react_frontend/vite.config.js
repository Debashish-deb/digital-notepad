import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = path.resolve(__dirname, '../../../../')
const DATABASE_ROOT = path.join(REPO_ROOT, 'database')
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
      '/health': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/database-static': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/projects': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/checklists': { target: 'http://localhost:8000', changeOrigin: true },
      '/notebook': { target: 'http://localhost:8000', changeOrigin: true },
      '/decisions': { target: 'http://localhost:8000', changeOrigin: true },
      '/tasks': { target: 'http://localhost:8000', changeOrigin: true },
      '/team': { target: 'http://localhost:8000', changeOrigin: true },
      '/stats': { target: 'http://localhost:8000', changeOrigin: true },
      '/ask': { target: 'http://localhost:8000', changeOrigin: true },
      '/csc-media': { target: 'http://localhost:8000', changeOrigin: true },
      '/projects-static': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
