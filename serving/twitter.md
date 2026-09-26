Qwen 3.8 27B is surprisingly fast on a MacBook 💻 

Running Youssofal/Qwen3.8-27B-MTPLX-Optimized-Quality on my M5 Max 128GB with MTPLX + MTP 2.

Real decode speeds:

• 1.5K context → 40.9 tok/s
• 8.2K context → 33.1 tok/s
• Auto-tune peak → 54.8 tok/s
• Base without MTP → 17.4 tok/s
• 3.14× speedup

And this is the 8-bit quality-first build, not the faster 4-bit version.

A dense 27B local model doing ~40 tok/s on a laptop is getting seriously usable.

Where are you running your Qwen 3.8, and what speeds are you getting? 

#Qwen #LocalAI

-------


https://x.com/LocalAiCherry/status/2090407651762917431


------

Uncensored Qwen3.8-27B now fits in 8 GB.

- 2-bit MLX build just dropped.
- Fully local 0 refusals 
- Fully uncensored.
& also 2,4,6,8-bit
- with Native vision
- 262K context

No CUDA, No cloud, Made for local red-teaming on Mac.

https://huggingface.co/orcarouter/Qwe

https://huggingface.co/orcarouter/Qwen3.8-27B-Uncensored-MLX

