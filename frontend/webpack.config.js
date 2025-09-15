const path = require('path');

module.exports = {
  entry: './src/main.js',
  output: {
    filename: 'bundle.js',
    path: path.resolve(__dirname, 'dist'),
    clean: true,
  },
  devServer: {
    static: {
      directory: path.join(__dirname, 'public'),
    },
    compress: true,
    port: 3000,
    open: true,
    historyApiFallback: true,
    hot: true,
    proxy: [
      {
        context: ['/api', '/health', '/info'],
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
      }
    ],
  },
  mode: 'development',
};
