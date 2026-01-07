import subprocess
import sys
import os
import statistics
import re
import time

def run_benchmark(iterations=5):
    print(f"开始启动性能基准测试 (执行 {iterations} 次迭代)...")
    print("-" * 50)
    times = []
    
    # Get the path to main.py relative to this script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    main_script = os.path.join(project_root, "main.py")
    
    # Use the same python executable running this script
    python_exe = sys.executable

    for i in range(iterations):
        print(f"运行 {i+1}/{iterations}...", end=" ", flush=True)
        try:
            # Run the application with --benchmark flag
            # We use a timeout to prevent hanging if something goes wrong
            result = subprocess.run(
                [python_exe, main_script, "--benchmark"],
                capture_output=True,
                text=True,
                cwd=project_root,
                timeout=30 
            )
            
            # Parse output for the magic string
            # Output format: BENCHMARK_STARTUP_TIME_MS: 1234.56
            match = re.search(r"BENCHMARK_STARTUP_TIME_MS:\s*([\d.]+)", result.stdout)
            
            if match:
                duration = float(match.group(1))
                times.append(duration)
                print(f"成功 ({duration:.2f} ms)")
            else:
                print("失败 (未找到时间输出)")
                # Print stdout/stderr for debugging if needed
                # print(result.stdout)
                # print(result.stderr)
        
        except subprocess.TimeoutExpired:
            print("失败 (超时)")
        except Exception as e:
            print(f"失败 ({str(e)})")
            
        # Small delay between runs
        time.sleep(1)

    print("-" * 50)
    if times:
        mean_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        stdev = statistics.stdev(times) if len(times) > 1 else 0
        
        print(f"测试结果 ({len(times)} 次成功运行):")
        print(f"  平均启动时间:    {mean_time:.2f} ms")
        print(f"  最小时间:        {min_time:.2f} ms")
        print(f"  最大时间:        {max_time:.2f} ms")
        print(f"  标准差:          {stdev:.2f} ms")
    else:
        print("未记录到成功的运行。")

if __name__ == "__main__":
    iterations = 5
    if len(sys.argv) > 1:
        try:
            iterations = int(sys.argv[1])
        except ValueError:
            pass
    run_benchmark(iterations)