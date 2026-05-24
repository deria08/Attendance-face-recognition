const { spawn } = require('child_process');

exports.getEmbedding = (imageUrl) => {
  return new Promise((resolve, reject) => {
    const process = spawn('python', [
      'python/generate_embedding.py',
      imageUrl
    ]);

    let data = '';
    let error = '';

    process.stdout.on('data', chunk => {
      data += chunk.toString();
    });

    process.stderr.on('data', err => {
      error += err.toString();
    });

    process.on('close', () => {
      if (error) {
        return reject(error);
      }

      try {
        const result = JSON.parse(data);

        if (result.error) {
          return reject(result.error);
        }

        resolve(result);
      } catch (err) {
        reject(err);
      }
    });
  });
};