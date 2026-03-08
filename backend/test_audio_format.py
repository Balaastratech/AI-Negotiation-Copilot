"""
Diagnostic test to verify the audio format being received from the frontend
"""
import asyncio
import struct

def analyze_pcm_chunk(pcm_bytes: bytes) -> dict:
    """Analyze a PCM audio chunk to verify format"""
    analysis = {
        "size_bytes": len(pcm_bytes),
        "is_even": len(pcm_bytes) % 2 == 0,
        "sample_count": len(pcm_bytes) // 2,
        "first_10_samples": [],
        "last_10_samples": [],
        "min_value": 32767,
        "max_value": -32768,
        "zero_count": 0,
        "clipped_count": 0,
    }
    
    if len(pcm_bytes) < 2:
        return analysis
    
    # Parse as signed 16-bit little-endian integers
    sample_count = len(pcm_bytes) // 2
    
    for i in range(min(10, sample_count)):
        offset = i * 2
        sample = struct.unpack('<h', pcm_bytes[offset:offset+2])[0]
        analysis["first_10_samples"].append(sample)
    
    for i in range(max(0, sample_count - 10), sample_count):
        offset = i * 2
        sample = struct.unpack('<h', pcm_bytes[offset:offset+2])[0]
        analysis["last_10_samples"].append(sample)
    
    # Analyze all samples
    for i in range(sample_count):
        offset = i * 2
        sample = struct.unpack('<h', pcm_bytes[offset:offset+2])[0]
        
        analysis["min_value"] = min(analysis["min_value"], sample)
        analysis["max_value"] = max(analysis["max_value"], sample)
        
        if sample == 0:
            analysis["zero_count"] += 1
        
        if sample == -32768 or sample == 32767:
            analysis["clipped_count"] += 1
    
    # Check for potential corruption patterns
    analysis["warnings"] = []
    
    if not analysis["is_even"]:
        analysis["warnings"].append("⚠ Odd byte count - incomplete sample!")
    
    if analysis["zero_count"] == sample_count:
        analysis["warnings"].append("⚠ All samples are zero - silence or corruption")
    
    if analysis["clipped_count"] > sample_count * 0.1:
        analysis["warnings"].append(f"⚠ {analysis['clipped_count']} clipped samples ({analysis['clipped_count']/sample_count*100:.1f}%)")
    
    if analysis["min_value"] == analysis["max_value"]:
        analysis["warnings"].append("⚠ All samples have same value - likely corruption")
    
    return analysis


def print_analysis(analysis: dict):
    """Pretty print the analysis"""
    print(f"\n{'='*60}")
    print(f"PCM Audio Chunk Analysis")
    print(f"{'='*60}")
    print(f"Size: {analysis['size_bytes']} bytes ({analysis['sample_count']} samples)")
    print(f"Duration: {analysis['sample_count'] / 16000:.3f} seconds @ 16kHz")
    print(f"Range: [{analysis['min_value']}, {analysis['max_value']}]")
    print(f"Zero samples: {analysis['zero_count']} ({analysis['zero_count']/max(1, analysis['sample_count'])*100:.1f}%)")
    print(f"Clipped samples: {analysis['clipped_count']} ({analysis['clipped_count']/max(1, analysis['sample_count'])*100:.1f}%)")
    
    print(f"\nFirst 10 samples: {analysis['first_10_samples']}")
    print(f"Last 10 samples: {analysis['last_10_samples']}")
    
    if analysis["warnings"]:
        print(f"\n⚠ WARNINGS:")
        for warning in analysis["warnings"]:
            print(f"  {warning}")
    else:
        print(f"\n✓ No obvious corruption detected")
    
    print(f"{'='*60}\n")


# Test with sample data
if __name__ == "__main__":
    # Test 1: Valid silence
    print("Test 1: Valid silence (all zeros)")
    silence = b'\x00' * 8192  # 4096 samples of silence
    analysis = analyze_pcm_chunk(silence)
    print_analysis(analysis)
    
    # Test 2: Valid sine wave
    print("\nTest 2: Valid sine wave")
    import math
    samples = []
    for i in range(4096):
        # 440 Hz sine wave at 16kHz
        value = int(16000 * math.sin(2 * math.pi * 440 * i / 16000))
        samples.append(struct.pack('<h', value))
    sine_wave = b''.join(samples)
    analysis = analyze_pcm_chunk(sine_wave)
    print_analysis(analysis)
    
    # Test 3: Corrupted (odd byte count)
    print("\nTest 3: Corrupted (odd byte count)")
    corrupted = b'\x00' * 8191  # Odd number of bytes
    analysis = analyze_pcm_chunk(corrupted)
    print_analysis(analysis)
    
    # Test 4: Clipped audio
    print("\nTest 4: Clipped audio")
    clipped = struct.pack('<h', 32767) * 4096
    analysis = analyze_pcm_chunk(clipped)
    print_analysis(analysis)
