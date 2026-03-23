import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

# Hide aesthetic warnings
warnings.filterwarnings('ignore')

# Set a professional academic style for the plots
sns.set_theme(style="whitegrid", palette="muted")

def generate_report_visuals():
    # 1. Load the CSV Data
    csv_file = "FYP_Master_Results_Database.csv"
    try:
        df = pd.read_csv(csv_file)
    except FileNotFoundError:
        print(f"❌ Error: Cannot find {csv_file}. Make sure it is in the same folder.")
        return

    # Calculate Total Engagement (Likes + Reactions)
    df['Total_Engagement'] = df['Simulated_Likes'] + df['Simulated_Total_Reactions']

    print("==================================================")
    print("🏆 FYP KEY PERFORMANCE METRICS (Copy to your Report)")
    print("==================================================")

    # Metric 1: Optimization Success Rate
    target_score = 15.0
    total_campaigns = len(df)
    success_campaigns = len(df[df['DB_Reward_Score (reward_rt)'] >= target_score])
    success_rate = (success_campaigns / total_campaigns) * 100
    print(f"1. Optimization Success Rate: {success_rate:.1f}% ({success_campaigns} out of {total_campaigns} campaigns succeeded).")

    # Metric 2: Top Performing Vibe
    vibe_rewards = df.groupby('Vibe')['DB_Reward_Score (reward_rt)'].mean().sort_values(ascending=False)
    top_vibe = vibe_rewards.index[0]
    top_vibe_score = vibe_rewards.iloc[0]
    print(f"2. Top Performing Vibe: The '{top_vibe}' vibe outperformed others with an average reward score of {top_vibe_score:.2f}.")

    # Metric 3: Average Engagement
    avg_engagement = df['Total_Engagement'].mean()
    avg_ctr = df['Simulated_CTR (%)'].mean()
    print(f"3. Average Engagement: The mean engagement across all optimized ads was {avg_engagement:.1f} interactions per ad.")
    print(f"4. Average CTR: {avg_ctr:.2f}%")
    print("==================================================\n")

    print("📊 Generating 6 High-Resolution Charts for your Figures...")

    # ---------------------------------------------------------
    # Chart 1: Average Reward Score by Vibe
    # ---------------------------------------------------------
    plt.figure(figsize=(8, 6))
    sns.barplot(data=df, x='Vibe', y='DB_Reward_Score (reward_rt)', errorbar=None, palette='viridis')
    plt.title('Average RL Reward Score by Creative Vibe', fontsize=14, fontweight='bold')
    plt.ylabel('Average Reward Score', fontsize=12)
    plt.xlabel('Campaign Vibe', fontsize=12)
    plt.axhline(y=15.0, color='r', linestyle='--', label='Target Success Threshold (15.0)')
    plt.legend()
    plt.tight_layout()
    plt.savefig('Chart1_Avg_Reward_By_Vibe.png', dpi=300)
    plt.close()

    # ---------------------------------------------------------
    # Chart 2: Average CTR by Vibe
    # ---------------------------------------------------------
    plt.figure(figsize=(8, 6))
    sns.barplot(data=df, x='Vibe', y='Simulated_CTR (%)', errorbar=None, palette='magma')
    plt.title('Average Click-Through Rate (CTR) by Vibe', fontsize=14, fontweight='bold')
    plt.ylabel('Average CTR (%)', fontsize=12)
    plt.xlabel('Campaign Vibe', fontsize=12)
    plt.tight_layout()
    plt.savefig('Chart2_Avg_CTR_By_Vibe.png', dpi=300)
    plt.close()

    # ---------------------------------------------------------
    # Chart 3: Scatter Plot - CTR vs. Total Engagement
    # ---------------------------------------------------------
    plt.figure(figsize=(8, 6))
    sns.scatterplot(data=df, x='Simulated_CTR (%)', y='Total_Engagement', hue='Vibe', s=150, palette='deep', alpha=0.8)
    plt.title('Ad Interaction: CTR vs. Total Engagement', fontsize=14, fontweight='bold')
    plt.ylabel('Total Engagement (Likes + Reactions)', fontsize=12)
    plt.xlabel('Click-Through Rate (%)', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig('Chart3_CTR_vs_Engagement.png', dpi=300)
    plt.close()

    # ---------------------------------------------------------
    # Chart 4: AI Virality Prediction vs. Actual Likes
    # ---------------------------------------------------------
    plt.figure(figsize=(8, 6))
    sns.regplot(data=df, x='DB_Like_Viral_Score (lv)', y='Simulated_Likes', scatter_kws={'s':100}, line_kws={"color": "red"})
    plt.title('AI Virality Prediction vs. Simulated Engagement', fontsize=14, fontweight='bold')
    plt.ylabel('Actual Simulated Likes', fontsize=12)
    plt.xlabel('AI Calculated Like/Viral Score (lv)', fontsize=12)
    plt.tight_layout()
    plt.savefig('Chart4_AI_Prediction_Accuracy.png', dpi=300)
    plt.close()

    # ---------------------------------------------------------
    # Chart 5: Box Plot - Variance of Reward Scores
    # ---------------------------------------------------------
    plt.figure(figsize=(8, 6))
    sns.boxplot(data=df, x='Vibe', y='DB_Reward_Score (reward_rt)', palette='Set2')
    sns.stripplot(data=df, x='Vibe', y='DB_Reward_Score (reward_rt)', color=".3", size=8, alpha=0.6)
    plt.title('Consistency of Reward Scores Across Vibes', fontsize=14, fontweight='bold')
    plt.ylabel('Reward Score Distribution', fontsize=12)
    plt.xlabel('Campaign Vibe', fontsize=12)
    plt.tight_layout()
    plt.savefig('Chart5_Reward_Variance_Boxplot.png', dpi=300)
    plt.close()

    # ---------------------------------------------------------
    # Chart 6: Pie Chart - Total Engagement Share
    # ---------------------------------------------------------
    plt.figure(figsize=(8, 8))
    engagement_by_vibe = df.groupby('Vibe')['Total_Engagement'].sum()
    plt.pie(engagement_by_vibe, labels=engagement_by_vibe.index, autopct='%1.1f%%', 
            startangle=140, colors=sns.color_palette('pastel'), explode=(0.05, 0.05, 0.05))
    plt.title('Total Engagement Share by Vibe', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('Chart6_Engagement_Share_Pie.png', dpi=300)
    plt.close()

    print("✅ SUCCESS! 6 High-Resolution PNG charts have been saved to your folder.")

if __name__ == "__main__":
    generate_report_visuals()