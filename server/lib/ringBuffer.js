class RingBuffer {
  constructor(capacity) {
    this.capacity = capacity;
    this.buffer = [];
  }

  push(item) {
    this.buffer.push(item);
    if (this.buffer.length > this.capacity) {
      this.buffer.shift();
    }
  }

  getAll() {
    return this.buffer;
  }
}

module.exports = RingBuffer;
