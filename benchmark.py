"""
benchmark.py

Compares two ways of looking up a response: checking a list one item at a
time (like a long if-elif chain would) vs. using a dictionary's .get().

This is meant to show why the chatbot uses a dictionary for its knowledge
base instead of a long chain of if/elif statements: as the number of rules
grows, list/if-elif lookup gets slower, but dictionary lookup stays fast.

Run with: python benchmark.py
"""

import timeit
import matplotlib.pyplot as plt


def linear_lookup(pairs, key):
    """Same idea as a long if/elif chain: check each item one by one."""
    for k, v in pairs:
        if k == key:
            return v
    return "I do not understand."


def dict_lookup(table, key):
    return table.get(key, "I do not understand.")


def run_benchmark():
    sizes = [10, 100, 500, 1000, 2000, 3000]
    list_times = []
    dict_times = []

    print(f"{'Rules':>8} | {'List (ms)':>12} | {'Dict (ms)':>12}")
    print("-" * 38)

    for n in sizes:
        pairs = [(f"kw_{i}", f"response_{i}") for i in range(n)]
        table = dict(pairs)
        worst_key = f"kw_{n - 1}"  # last item = worst case for a linear scan

        t_list = timeit.timeit(lambda: linear_lookup(pairs, worst_key), number=200) * 1000
        t_dict = timeit.timeit(lambda: dict_lookup(table, worst_key), number=200) * 1000

        list_times.append(t_list)
        dict_times.append(t_dict)
        print(f"{n:>8} | {t_list:>12.4f} | {t_dict:>12.4f}")

    return sizes, list_times, dict_times


def plot_results(sizes, list_times, dict_times):
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(8, 5))

    ax.plot(sizes, list_times, color="#FF6B4A", marker="o", label="List scan (like if-elif)")
    ax.plot(sizes, dict_times, color="#4ADE80", marker="o", label="Dictionary .get()")

    ax.set_title("Lookup speed: list scan vs dictionary")
    ax.set_xlabel("Number of rules")
    ax.set_ylabel("Time (ms)")
    ax.legend()
    ax.grid(alpha=0.2)

    fig.tight_layout()
    fig.savefig("efficiency_proof.png", dpi=150)
    print("\nSaved chart -> efficiency_proof.png")


if __name__ == "__main__":
    sizes, list_times, dict_times = run_benchmark()
    plot_results(sizes, list_times, dict_times)
