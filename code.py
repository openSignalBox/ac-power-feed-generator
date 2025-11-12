import array, math, time, board, audiobusio, digitalio, audiocore
import math

SAMPLE_RATE = 44100  # Default sample rate for audio DAC
AMPLITUDE = 0.72  # Calibrate to max amp setting = nominal voltage (e.g. 100 V)
FREQ_LOW = 100.0 / 3.0  # 33.333... Hz
FREQ_HIGH = 125.0  # 125 Hz

# Switch setup for frequency toggling
sw_left = digitalio.DigitalInOut(board.GP14)
sw_left.switch_to_input(pull=digitalio.Pull.UP)

sw_right = digitalio.DigitalInOut(board.GP15)
sw_right.switch_to_input(pull=digitalio.Pull.UP)


# Helper function: generate sine samples for given freq and length
def sine_array(
    freq, length, sample_rate=SAMPLE_RATE, amplitude=AMPLITUDE, phase_offset=0.0
):
    arr = array.array("h", [0] * length)
    for i in range(length):
        phase = 2 * math.pi * freq * i / sample_rate + phase_offset
        arr[i] = int(32767 * amplitude * math.sin(phase))
    return arr


# Helper function: build stereo buffer with same frame length
# Offset right channel by quarter phase to provide for dual element vane relays
def stereo_wave(freq_left, freq_right):
    """Generate a stereo interleaved buffer that loops cleanly."""

    # Determine total samples that fit integer cycles for both freqs to avoid clicks
    min_continuous_samples = 5292  # LCM of sample rate / freq fractions' denominators
    total_length = min_continuous_samples
    print(f"Generating stereo buffer length: {total_length} samples")

    left = sine_array(freq_left, total_length)
    right = sine_array(
        freq_right,
        total_length,
        phase_offset=math.pi / 2,
    )

    stereo = array.array("h", [0] * (2 * total_length))
    for i in range(total_length):
        stereo[2 * i] = left[i]
        stereo[2 * i + 1] = right[i]
    stereo_wave_sample = audiocore.RawSample(
        stereo, channel_count=2, sample_rate=SAMPLE_RATE
    )
    return stereo_wave_sample


# I2S setup - internal pins for audio hat
bck = board.GP10
lrck = board.GP11
data = board.GP9
audio = audiobusio.I2SOut(bit_clock=bck, word_select=lrck, data=data)

# Initial state of switches
left_high = False
right_high = False

wave = stereo_wave(FREQ_LOW, FREQ_LOW)
# wave = stereo_wave(FREQ_HIGH, FREQ_HIGH)
audio.play(wave, loop=True)

print("Stereo sine started")

# Main loop: monitor switches and update frequencies
while True:
    new_left_high = not sw_left.value
    new_right_high = not sw_right.value

    if new_left_high != left_high or new_right_high != right_high:
        left_high = new_left_high
        right_high = new_right_high

        fl = FREQ_HIGH if left_high else FREQ_LOW
        fr = FREQ_HIGH if right_high else FREQ_LOW

        audio.stop()
        wave = stereo_wave(fl, fr)
        audio.play(wave, loop=True)

        print(f"Updated: Left={fl:.2f} Hz, Right={fr:.2f} Hz")

    time.sleep(0.1)
