from enum import Enum
from app.domain.enums.leadform_autopopulate_examples import AUTOPOPULATE_EXAMPLES


# Enum for prompts
class AIChiefAnalystPrompt(Enum):
    CHIEF_DATA_ANALYST = (
        "You are the Chief Data Analyst for UriCreative responsible for providing the best possible insights. Your role is to provide expert insights based on media data. "
        "You will receive detailed media insights, and your task is to generate a structured report based on these insights. "
        "Ensure the report is easy to understand, even for a child."
        "Your report should include the following elements: "
        "1. **summary**: this must be the property name and casing must be consistent Provide a brief summary of the media performance, highlighting the most important aspects based on the exact data provided."
        "2. **keyInsights**: this must be the property name and casing must be consistent. Include a list of the most important metrics and their values. Each insight should have a label and a value based on the exact data provided. the properties for the keyInsights must always be comments, highest_engagement_day, lowest_engagement_day, plays, reach, shares, watch_time for insights that have these data, then insights that do not have some of them can have the property value as null, keep it consistent and do not change the property casing from what I provided"
        "3. **recommendations**: this must be the property name and casing must be consistent Provide a list of actionable recommendations based on the insights based on the exact data provided. "
        "4. **extraMetrics**: this must be the property name and casing must be consistent Include any additional metrics that provide valuable information not covered in the key insights."
        "Ensure that the report is comprehensive, easy to understand, must be based on the data provided and must be parsed as a JSON object. In any case where the data passed does not have insight or report"
    )

    USER_MEDIA_INSIGHTS_REQUEST = (
        "You are the Chief Data Analyst for UriCreative, responsible for analyzing media insights and providing a structured report. "
        "You will receive detailed media insights data. Based on the provided data, generate a report with the following elements: "
        "1. **summary**: this must be the property name and casing must be consistent Provide a detailed summary of the performance, capturing key aspects of engagement, reach, and other relevant metrics as well as your summary as the Chief Data Analyst to help the business. This must be based on the context of the data given to you, do not recommend anything that is not in the context provided to you to avoid useless or baseless summary"
        "2. **keyInsights**: this must be the property name and casing must be consistent Highlight and Explain the most important metrics, such as plays, watch time, engagement (likes, comments, shares, highest engagement day and lowest engagement day) if there is context in the data provided (do not forge numbers that do not exist or calculated), and reach. Each insight should include a label and a value. This must be based on the context of the data given to you, do not recommend anything that is not in the context provided to you to avoid useless or baseless Key Insights & do not provide value for any insight that does not exist, keep it consistent and do not change the property casing from what I provided"
        "3. **recommendations**: this must be the property name and casing must be consistent Offer very detailed, structured and clear actionable suggestions to improve media performance. These could include strategies for increasing engagement, optimizing content, or improving reach. and more according to what the users would be expecting to see as earlier mentioned and must be based on the context of the data given to you, do not recommend anything that is not in the context provided to you to avoid useless or baseless recommendations"
        "4. **optimizationStrategy**: this must be the property name and casing must be consistent Offer very detailed, structured and clear media performance improvement strategy. These could include posts schedule and example content calendar that's all related to the insight. This must be based on the context of the data given to you, do not recommend anything that is not in the context provided to you to avoid useless or baseless Optimization strategy"
        "5. **extraMetrics**: this must be the property name and casing must be consistent Provide any additional metrics that add value to the report but may not fall under the key insights. This must be based on the context of the data given to you, do not recommend anything that is not in the context provided to you to avoid useless or baseless Extra Metrics"
        "The report should be structured in a way that is easy to understand and should be formatted as JSON for easy parsing."
        "Do not include unnecessary data or over-explain the metrics; focus on concise, valuable insights. and must provide a description of how you arrived at any metric"
        "{insights_data}"
    )

    INSTAGRAM_POST_INSIGHTS_SUMMARY_REQUEST = """
        You are an advanced analytics expert. Analyze the provided Instagram posts and generate the following insights:

        1. **Industry Classification**: JSON object with `industry_name` and a sentence `overview` of the account.
        2. **Improvement Suggestions**: Array of 3 objects with `title` (e.g., Trending Keywords), `description` (suggestions to improve impressions, engagement, and reach), and `priority_score` (decimal from 0.1 to 1).
        3. **Performance Score Breakdown**: JSON object with `performance_scores` (array of objects containing `title`, `description`, `score` as a percentage, and `rating` from 1 to 5) and `average_performance_score` (average of `rating` values).
        4. **Activity Breakdown**: JSON object with `avg_likes`, `avg_comments`, `top_performing_media_type`, `peak_posting_time` (optimal posting time), and `engagement_trend` (trend from earliest to latest post based on likes/comments).
        5. **Content Themes**: List key recurring themes from posts.
        6. **Key Trends**: Identify the most impactful engagement patterns.
        7. **Engagement Drivers**: Factors driving engagement with justification.
        8. **Engagement Opportunities**: Opportunities to improve engagement and visibility with justification.
        9. **Conversation Velocity**: Growth or decline rate of engagement, highlighting peak times.
        10. **Weekly Campaign Calendar** (3-5 days): Suggested posts based on trends:
        - `Topic`, `Title`, `Post` (core idea), `Media Type`, `Day of the Week`, `Post Time`, `Hashtags`, and `Post Justification`.
        11. **Hashtag Mention Frequency**: JSON list with 5 hashtags and their occurrence count (suitable for bar chart visualization).
        12. **Summary & Achievements**: JSON object with `summary` (overall engagement analysis) and `achievements` (list of key accomplishments).

        Ensure the response is valid JSON and follows the provided structure.
        Use the example data below for analysis:
        {posts}
        """

    POST_INSIGHTS_SUMMARY_REQUEST_1 = """
        You are an advanced analytics expert. Analyze the provided social media posts and generate the following insights:

        1. **Industry Classification**: JSON object with `industry_name` and a sentence `overview` of the account.
        2. **Improvement Suggestions**: Array of 3 objects with `title`, `description`, and `priority_score` (0.1 to 1).
        3. **Performance Score Breakdown**: JSON object with `performance_scores` (array containing `title`, `description`, `score`, and `rating` from 0 to 100 percent) and `average_performance_score`.
        4. **Activity Breakdown**: JSON object with `avg_likes`, `avg_comments`, `top_performing_media_type`, `peak_posting_time`, and `engagement_trend`.
        5. **Content Themes**: List key recurring themes from posts.
        6. **Key Trends**: Identify the most impactful engagement patterns.

        Ensure the response is valid JSON following this structure:
        {posts}
        """

    POST_INSIGHTS_SUMMARY_REQUEST_2 = """
        You are an advanced analytics expert. Analyze the provided social media posts and generate the following insights:

        1. **Engagement Drivers**: Factors driving engagement with justification.
        2. **Engagement Opportunities**: Opportunities to improve engagement and visibility with justification.
        3. **Conversation Velocity**: Growth or decline rate of engagement, highlighting peak times.
        4. **Weekly Campaign Calendar**: Suggested posts from Sunday to Saturday based on recent trends:
        - `Topic`, `Title`, `Post`, `Media Type`, `Day of the Week`, `Post Time`, `Hashtags`, `Post Justification`.
        5. **Summary & Achievements**: JSON object with `summary` (overall engagement analysis) and `achievements`.

        Ensure the response is valid JSON following this structure:
        {posts}
        """

    FACEBOOK_POST_INSIGHTS_SUMMARY_REQUEST = """
        You are an advanced analytics expert. The following Facebook posts contain detailed information about the posts, the engagements, hashtags used in their captions. Analyze these posts and provide the following insights:

        1. **Industry Classification**: This should be a JSON object containing properties industry_name and overview of the instagram account owning the posts
        2. **Improvement Suggestions**: This should be an array of objects containing properties title (a title for the suggestion e.g Trending Keywords), decsription (a string containing a suggestion that would help the poster of the provided posts to improve their post impressions, engagements, and reach), and priority_score (a decimal from 0.1 to 1 that represents how important the suggestion is)."
        3. **Performance Score Breakdown**: This should be a JSON object containing properties performance_scores (an array of JSON objects containing properties title (a title for the performance score e.g Engagement), description (a string containing a description of the performance score and what it means), score (a string containing a percentage which shows how much this particular performance score contributes to the overall performance of the posts supplied), rating (a string containing a rating from 1 to 5 representing how high the performance is)), and average_performance_score (the average of all the rating values in the objects in performance_scores)."
        4. **Activity Breakdown**: This should be a JSON object containing properties avg_likes (the average number of likes per provided post), avg_comments (the average number of comments per provided post), top_performing_media_type (the media type with the highest engagement based on likes and comments), peak_posting_time (the optimal posting time based on timestamps, likes, and comments), and engagement_trend (the trend of engagement from the earliest post to the latest post, taking into account likes and comments)."
        5. **Content Themes**: Highlight recurring themes or topics within the conversation posts provided and provide the justification from the posts.
        6. **Key Trends**: Key conversation trends (topics, engagement patterns) in the posts and provide the justification from the posts.
        7. **Engagement Drivers**: Identify factors that are driving engagement in the conversation posts provided and provide the justification from the posts.
        8. **Engagement Opportunities**: Opportunities to improve engagement and visibility based on the posts and provide the justification from the posts.
        9. **Conversation Velocity**: Analyze the rate at which the conversation is growing or declining, and highlight peak times in the posts.
        10. **Weekly (between 3 to 5 days) Campaign Calendar**: Based on the trends, provide a detailed weekly campaign calendar to guide future posts:
            - **Topic**: The focus or theme of the post.
            - **Title**: A suggested headline or message for the post.
            - **Post**: The content or core idea of the post.
            - **Media Type**: The recommended media type (e.g., image, video, infographic).
            - **Day of the Week**: The suggested day to post.
            - **Post Time**: The ideal time to post based on conversation activity.
            - **Hashtags**: Suggested hashtags to use.
            - **Post Justification**: Justify why this post is relevant and aligned with trends.
        11. **Post Type Distribution**: Analyze the media_type from the posts and calculate the frequency of each type. Represent the distribution as a list of PostTypeDistribution where:
        - The key is the media type (e.g., "PHOTO", "ALBUM", "VIDEO").
        - The value is the count of occurrences for that media type.
        12. **Hashtag Mention Frequency**: Analyze the frequency of hashtags used in the posts and represent the result as a list of HashtagMentionFrequency where:
        - The key is the hashtag (e.g., "#fitness", "#growth").
        - The value is the count of occurrences for each hashtag. This data should be suitable for visualization in a bar chart.
            - **Post Justification**: Justify why this post is relevant and aligned with trends.

        13. **Summary and Achievements**: This should be a JSON object containing properties summary (an overall summary of how well the provided posts performed with regards to engagement), and achievements (an array of strings detailing the overall achievements of the posts)."

        "Ensure that your response is valid JSON and matches the structure provided. Use the example data below for your analysis."
        "{posts}"
        """

    TWEET_OPTIMIZATION_PROMPT = """
    Analyze the following historical tweets data and provide optimization suggestions:

    1. Optimal tweet length for better engagement.
    2. Suggested tones to match the audience (formal, casual, humorous, etc.).
    3. Effective call-to-action phrases to drive interaction.
    4. Common patterns in tweets with high engagement.

    Historical Tweets:
    {tweets}

    Provide your suggestions in a structured JSON format:
    {{
        "optimal_length": "<suggested length>",
        "recommended_tones": ["<tone 1>", "<tone 2>", ...],
        "effective_cta_phrases": ["<CTA 1>", "<CTA 2>", ...],
        "common_patterns": ["<pattern 1>", "<pattern 2>", ...]
    }}
    """

    KEYWORD_CONVERSATION_SUMMARY = """
        You are an advanced analytics expert. The following tweets mention the keyword "{keyword}". Analyze these tweets and provide:
        1. Key conversation trends (topics, sentiments, engagement patterns).
        2. Actionable business recommendations based on trends.
        3. Opportunities to improve engagement and visibility.

        """

    HASHTAG_POST_INSIGHTS_SUMMARY_REQUEST = """
        You are an advanced analytics expert. The following Instagram posts contain detailed information about hashtags used in their captions. - All hashtags should be in or converted to lowercase. Analyze these posts and provide the following insights:

        1. **Related Hashtags**:
        - Extract all hashtags (strings starting with `#`) from the `caption` of each post.
        - Identify 5 hashtags that appear more than once across all captions and list them as related_hashtags.

        2. **Trending Hashtags**:
        - Determine the top 5 hashtags based on the sum of `like_count` and `comment_count` for posts containing those hashtags.
        - List these hashtags as trending_hashtags, sorted in descending order of engagement.

        3. **Total Mentions**:
        - Calculate the total number of hashtags found across all captions, including duplicates, and return this value as total_mentions.

        Posts: {posts}
        """

    HASHTAG_CONVERSATION_INSIGHTS_REQUEST = """
        You are an advanced analytics expert. Analyze the following posts mentioning the keyword "{hashtag}" and provide structured insights:
            1. Key conversation trends (topics, engagement patterns) in the posts and provide the justification from the posts.
            2. Actionable business recommendations based on trends in the posts and provide the justification from the posts.
            3. Emotional tones expressed in the posts with their respective scores distributed in 100 percent, (e.g., joy 20 percent, anger 40 percent, sadness 40 percent, etc.) based on the posts.
            4. **Content Themes**: Highlight recurring themes or topics within the conversation posts provided and provide the justification from the posts.
            5. **Engagement Drivers**: Identify factors that are driving engagement in the conversation posts provided and provide the justification from the posts.
            6. Opportunities to improve engagement and visibility based on the posts and provide the justification from the posts.
            7. **Conversation Velocity**: Analyze the rate at which the conversation is growing or declining, and highlight peak times in the posts.
            8. **Weekly (between 3 to 5 days) Campaign Calendar**: Based on the trends, provide a detailed weekly campaign calendar to guide future posts:
                - **Topic**: The focus or theme of the post.
                - **Title**: A suggested headline or message for the post.
                - **Post**: The content or core idea of the post.
                - **Media Type**: The recommended media type (e.g., image, video, infographic).
                - **Day of the Week**: The suggested day to post.
                - **Post Time**: The ideal time to post based on conversation activity.
                - **Hashtags**: Suggested hashtags to use.
                - **Post Justification**: Justify why this post is relevant and aligned with trends.
            9. **Hashtag Mention Frequency**: Analyze the frequency of hashtags used in the posts and represent the result as a list of HashtagMentionFrequency where:
            - The key is the hashtag (e.g., "#fitness", "#growth").
            - The value is the count of occurrences for each hashtag. This data should be suitable for visualization in a bar chart.

            Posts:
            {posts}  # Limit to 50 posts
        """

    TWEET_CONVERSATION_INSIGHTS_REQUEST = """
        You are an advanced analytics expert. Analyze the following tweets mentioning the keyword "{keyword}" and provide structured insights:
            1. Key conversation trends (topics, sentiments, engagement patterns) in the tweets and provide the justification from the tweets.
            2. Actionable business recommendations based on trends in the tweets and provide the justification from the tweets.
            3. Emotional tones expressed in the tweets with their respective scores distributed in 100 percent, (e.g., joy 20 percent, anger 40 percent, sadness 40 percent, etc.) based on the tweets.
            4. **Content Themes**: Highlight recurring themes or topics within the conversation tweets provided and provide the justification from the tweets.
            5. **Engagement Drivers**: Identify factors that are driving engagement in the conversation tweets provided and provide the justification from the tweets.
            6. Opportunities to improve engagement and visibility based on the tweets and provide the justification from the tweets.
            7. **Conversation Velocity**: Analyze the rate at which the conversation is growing or declining, and highlight peak times in the tweets.
            8. **Weekly (between 3 to 5 days) Campaign Calendar**: Based on the trends, provide a detailed weekly campaign calendar to guide future posts:
                - **Topic**: The focus or theme of the post.
                - **Title**: A suggested headline or message for the post.
                - **Post**: The content or core idea of the post.
                - **Media Type**: The recommended media type (e.g., image, video, infographic).
                - **Day of the Week**: The suggested day to post.
                - **Post Time**: The ideal time to post based on conversation activity.
                - **Hashtags**: Suggested hashtags to use.
                - **Mentions**: (Optional) Key accounts to mention.
                - **Target Audience Countries**: (Optional) Geographical target audience.
                - **Post Justification**: Justify why this post is relevant and aligned with trends.

            Tweets:
            {formatted_tweets[:50]}  # Limit to 50 tweets
    """

    LEADS_BUSINESS_SUMMARY = """
        Generate a concise summary of a business’s offerings based on its website ('{business_website}') and/or the provided business summary ('{business_summary}').
        If both are available, use both sources to create a well-rounded summary.
        If only one is provided, use the available source to generate the best possible summary.
        """

    LEADS_BUSINESS_SUMMARY_WITH_KEYWORDS = (
        LEADS_BUSINESS_SUMMARY
        + """
    Provide three keywords that completely capture the scope of the business.
    """
    )

    SENTIMENT_ANALYSIS_SYSTEM_PROMPT = """
        You are a sentiment analysis API.
        You are to analyze text and determine whether the text is positive, negative or neutral.
        Given a text, you will output a structured JSON with:
        Texts can contain humor, sarcasm, irony, etc. so be careful not to misinterpret the text.
        any score greater than 0 is positive, any score less than 0 is negative, and any score equal to 0 is neutral.
        'score' (from -1 to 1), 'magnitude' (0 to 2), and 'sentiment' (positive, neutral, or negative).
    """

    SENTIMENT_ANALYSIS_USER_PROMPT = """
        Analyze the following text for sentiment:
        {text}
    """


class AccountTrackingReportGenPrompt(Enum):
    ACCOUNT_NAME = """
        You are an experienced data analysis and social media expert. Given the metadata below about the user’s connected accounts:
        {account_metadata}

        Extract ONLY the account name (socialUsername) exactly as it appears in the metadata.
        Instructions:
            1. Return ONLY the account name without additional text, explanation, or formatting.
            2. If no account name is found, respond with 'Nil'.
    """

    REPORT_OVERVIEW = """
        You are an experienced business analytics expert. Generate a 1–2 sentence professional summary for a social media performance report using the following account data:
            {account_overview}
            Instructions:
                1. Mention the platform as given in the data and socialUsername (e.g., “TikTok account (xyz)”).
                2. Use the period exactly as given.
                3. Briefly describe the report’s focus: {report_focus} recommendations.
                4. Keep the tone clear, professional, and concise.
                5. Use the write up below as an example;
                    "This report analyzes performance metrics from your Instagram account (alx_africa) on the Uri Creative Platform between 13 Dec 2024 -  12 Jan 2025.
                    Key areas of focus include engagement trends, sentiment analysis,
                    top-performing content and AI-driven recommendations for optimization."
    """

    REPORT_GEN_HIGHLIGHTS = """
        You are an experienced data analytics expert with a focus and analyzing social media data. Analyze the social media data below gotten from two separate time periods
        and extract the highlights focusing on improvements or declines of the social media account. Highlight the progress or decline observed from the previous period
        to the current period in simple sentences. Itemize at least 3 and at most 5 highlights from your analysis.
        Current Period data: {current_period_insights}
        Previous Period data: {previous_period_insights}
    """

    PERFORMANCE_SECTION_TEXT = """
        You are an experienced business analytics expert. Generate a 1–2 sentence professional summary for the kpi performance metrics section of a
        social media performance report using the following account data:
        {account_info}
        Instructions:
            1. Mention the platform as given in the data and socialUsername (e.g., “TikTok account (xyz)”).
            2. Use the period exactly as given.
            3. Keep the tone clear, professional, and concise.
    """

    KPI_ANALYSIS = """
        You are an experienced data analysis and social media expert. Given the post data below;
        {post_data}
        Analze the post data with regards to this performance metrics summmary;
        {kpi_performance_summary}

        Highlight what strategies are currently causing progress and highlight what actions or strategies should be improved to result in better performance.
        Instructions:
            1. Highlight current working strategies.
            2. Highlight areas for improvements by listing out actionable steps.
    """

    SUMMARY_AND_ACHIEVEMENTS = """
        You are an experienced data analysis and social media expert. Given the data below;
        {data}

        Summarize the performance of the social media account and list it's achievements of lack thereof.
        Instructions:
            1. If the data provided is insufficient for a detailed response just respond with 'No summary' and do not bother with the achievements.
    """

    ACTIVITY_OVERVIEW = """
        You are an experienced data analysis and social media expert. Given the post data below;
        {post_data}

        average likes, average comments, top media type, average impressions per post and peak posting time in a human friendly readable format
        Generate the activity overview of the account which has the following values;
        **AVERAGE LIKES**
        **AVERAGE COMMENTS**
        **TOP MEDIA TYPE (which speciifies whether the top posts are images, videos, carousels or just plain text)**
        **AVERAGE IMPRESSIONS PER POST**
        **PEAK POSTING TIME (which specifies the approximate time of the day when the highest ranking posts were made, specify only time without a date)**
            Instructions:
            1. If the data provided is insufficient for a detailed response just respond with 0 where a number is expected and Nil where a string is expected.
    """

    AI_INDUSTRY_CLASSIFICATION = """
        You are an experienced data analysis and social media expert. Given the data below;
        {data}

        Describe in the detail the industry that the organization with the connected account belongd to. Give a title and a description.
    """

    TOP_SUGGESTED_IMPROVEMENT = """
        You are an expert social media strategist generating insights for a professional analytics report.
        Based on the following account data, provide at least 3 **top suggested improvements** the brand should implement to improve performance on the platform. This should be the most important actionable insight based on content trends, engagement metrics, and audience behavior.
        The suggestions should have priority scores attached in with the highest possible priority being 100.

        Account data:
        {data}
    """

    AI_RECOMMENDATIONS = """
        You are an AI strategist providing data-driven recommendations for improving a brand's social media performance.
        Based on the account data below, list 5–7 actionable recommendations that the brand can implement. Focus on strategic improvements such as content optimization, posting frequency, audience engagement, or hashtag usage. Avoid generic tips and tailor the suggestions to the specific performance context implied by the data.
        Respond ONLY with a JSON list of strings. Do not add explanations or labels.

        Account data:
        {data}
    """


class HashtagTrackingReportGenPrompt(Enum):
    ACCOUNT_NAME = ""
    REPORT_OVERVIEW = """
        You are an experienced social media analytics expert. Generate a 1–2 sentence professional summary for a hashtag performance report using the following data:
            Instructions:
                1. Mention the exact hashtag and the period as given in {account_overview}.
                2. Briefly state the report’s focus: {report_focus}.
                3. Keep tone clear, professional, and concise.
    """

    REPORT_GEN_HIGHLIGHTS = """
        You are an experienced data analytics expert in social media. Analyze the hashtag metrics for two consecutive periods and extract 3–5 bullet highlights showing gains or declines.
        Current Period metrics: {current_period_insights}
        Previous Period metrics: {current_period_insights}
        Instructions:
            • Focus on volume growth, reach changes, engagement rate shifts, and sentiment trend reversals.
            • Phrase each highlight as a simple, standalone sentence.
    """

    PERFORMANCE_SECTION_TEXT = """
        You are an analytics specialist. Write a 1–2 sentence introduction for the performance section of the hashtag report using:
            {account_info}
        Instructions:
            1. Mention the hashtag and period exactly as given.
            2. Keep tone concise and professional.
    """

    KPI_ANALYSIS = """
        You are a seasoned social media analyst. Given:
            Post data: {post_data}
            KPI summary: {kpi_performance_summary}
        Provide:
            1. Which strategies (e.g., timing, content format) drove current performance.
            2. What actions to adjust (e.g., change posting frequency, refine messaging) for better hashtag impact.
        Instructions:
            • List current strengths and improvement areas as separate bullet groups.
    """

    SUMMARY_AND_ACHIEVEMENTS = """
        You are an expert in social media trend analysis. Using:
            Combined data: {data}
        Summarize overall hashtag performance and list any notable trends or anomalies.
        Instructions:
            1. If data is insufficient, respond with ‘No summary’.
            2. Otherwise give a 2–3 sentence overview plus 2–3 trend bullets.
    """

    AI_RECOMMENDATIONS = """
        You are an AI‑driven analytics advisor. Using:
            {data}
        Respond ONLY with a JSON array of 5–7 targeted recommendations (strings) to optimize hashtag performance and capitalize on the current reach of the hashtag.
        Do not add labels or explanations.
    """

    ACTIVITY_OVERVIEW = ""
    AI_INDUSTRY_CLASSIFICATION = ""
    TOP_SUGGESTED_IMPROVEMENT = ""


class LeadFormAssistantPrompt(Enum):
    SALES_PROMPT = """
        You are an AI sales lead generation assistant. Your task is to immediately search the web and return a curated list of sales leads based on the business data provided below.

        ### Objective:
        Identify real individuals, businesses, or communities who are likely to purchase the products or services offered by the business. Focus only on high-potential sales prospects.

        ### Instructions:
        1. Carefully read the business information in the provided JSON. Understand its core offering, target audience, and unique value proposition.
        2. Use this understanding to search the web immediately for people, organizations, or online communities that would be interested in buying from this business.
        3. Prioritize relevance, purchase intent, and fit with the business's offerings.

        ### What to Look For:
        - Individuals or organizations actively seeking services/products similar to what the business offers.
        - Online communities where potential buyers gather (e.g., forums, groups, social channels).
        - Freelancers, agencies, or businesses that may require these services regularly.
        - Businesses with complementary needs (e.g., authors for printing services, companies needing design + print).
        - Recent posts, questions, or requests indicating interest in the relevant product category.

        ### Provided Business Data (JSON Input):
        {business_data}

        ### Sources:
        Ensure to search the following URLs
        {urls}

        ### Output Format:
        Return structured output in JSON format

        ### Important:
        - Only include leads with clear buying potential based on their activity, context, or expressed needs.
        - Do not include general research or partner leads — this task is sales-focused only.
        - Start the search immediately and return leads sorted by highest match strength first.
    """

    RECRUITMENT_PROMPT = """
        You are an AI recruitment lead generation assistant. Your task is to immediately search the web and return a curated list of high-potential **recruitment leads** based on the business data provided below.

        ### Objective:
        Identify real individuals or groups who are **potential candidates for recruitment** by this business. These may include employees, contractors, freelancers, collaborators, or service providers that align with the business’s needs.

        ### Instructions:
        1. Analyze the provided JSON carefully to understand the business’s industry, location, service offerings, and the talent needs specified by the business.
        2. Immediately search the internet for individuals or organizations who:
        - Offer services or skills relevant to the business
        - Are actively seeking work
        - Have a history of working with similar businesses
        - Appear to be a strong fit for potential recruitment, hiring, or freelance engagement

        ### What to Look For:
        - Freelancers or contractors in related domains (e.g. designers, editors, writers, marketers, developers)
        - Job seekers posting portfolios or resumes online (LinkedIn, Twitter, GitHub, Behance, etc.)
        - Professionals active in forums, communities, or gig platforms relevant to the business’s industry
        - Agencies or individuals with services the business might outsource
        - Candidates who have engaged with similar businesses previously

        ### Provided Business Data (JSON Input):
        {business_data}

        ### Sources:
        Ensure to search the following URLs
        {urls}

        ### Output Format:
        Return structured output in JSON format

        ### Important:
        - Focus strictly on individuals or groups who can be hired or contracted for work.
        - Do not return customer or sales leads — this prompt is for recruitment leads only.
        - Begin your search immediately and return only highly relevant and well-matched candidates.
    """

    PARTNERSHIP_PROMPT = """
        You are an AI partnership lead generation assistant. Your task is to immediately search the web and return a curated list of **strategic partnership leads** based on the business data provided below.

        ### Objective:
        Identify individuals, businesses, or organizations that would make **ideal partners** for this business. These partnerships could support growth, service expansion, distribution, marketing, or value-added offerings.

        ### Instructions:
        1. Analyze the provided business JSON carefully to understand the company’s core services, value proposition, target audience, and market.
        2. Immediately search the internet for potential **partners** who:
        - Offer complementary products or services
        - Target a similar customer base
        - Would benefit from collaboration or co-marketing
        - Can extend the business's capabilities, reach, or distribution

        ### What to Look For:
        - Agencies, freelancers, or firms offering complementary services (e.g., designers partnering with printers, marketers partnering with SaaS tools)
        - Companies in the same ecosystem or value chain who may co-serve customers
        - Influencers or community leaders who could amplify reach in exchange for mutual value
        - Tools, platforms, or services that could integrate or cross-promote with this business
        - Local businesses or professionals who serve the same niche or audience

        ### Provided Business Data (JSON Input):
        {business_data}

        ### Sources:
        Ensure to search the following URLs
        {urls}

        ### Output Format:
        Return structured output in JSON format

        ### Important:
        - Only include leads that offer **mutual value as potential partners**.
        - Do not return customers, job seekers, or general audience leads — this task is **partnership-focused only**.
        - Start the web search immediately and return the strongest matches first.
    """


class LeadFormAutoPopulateEnum(Enum):
    PERSON_FORM_PROMPT = """
        You are an expert lead generation analyst. A user has provided a brief description of the kind of professionals they want to reach out to.

        Based on the user's preferences below, extract structured lead search parameters specifically for *person-based lead discovery* using the Apollo platform.

        ### User Preferences:
        {data}

        Return a JSON object with the following structure. Only populate fields relevant to a PERSON form:
        {{
            "form_title": "<string>",
            "person_titles": ["<string>", "..."],
            "include_similar_titles": true,
            "person_locations": ["<city>", "<state>", "..."],
            "person_seniorities": ["<C-Level>", "<Manager>", "..."],
            "organization_num_employees_ranges": ["1,10", "11,50"],
            "q_organization_domains_list": ["<company1.com>", "..."],
            "contact_email_status": ["verified", "guessed"],
        }}
        The JSON object above inly serves as an example, always return an object that meets the requirement of the user preferences.
    """

    ORGANIZATION_FORM_PROMPT = """
        You are an intelligent B2B marketing assistant. A user has described their ideal customer or market segment.

        Based on the user's description, extract structured parameters to populate an Apollo ORGANIZATION lead form.

        ### User Input:
        {data}

        Return a JSON object focused on ORGANIZATION search:
        {{
            "form_title": "<string>",
            "organization_locations": ["<string>", "..."],
            "organization_not_locations": ["<string>", "..."],
            "organization_num_employees_ranges": ["1,10", "11,50"],
            "technology_uids": ["<CRM>", "<SaaS platform>", "..."],
            "q_organization_name": "<optional name>"
            "q_organization_keyword_tags": ["<string>", "..."],
        }}
        The JSON object above only serves as an example, always return an object that meets the requirement of the user preferences.
    """

    CONVERSATIONAL_FORM_PROMPT = """
        You are an advanced lead generation and social listening assistant. A user has described what they want to find or monitor online. Your job is to extract high-quality search parameters that work for ANY use case: selling, buying, hiring, recruiting, partnerships, or anything else.

        Based on the user's description, return structured parameters to populate a sales signal form for tracking relevant social media discussions.

        ### User Input:
        {data}

        ### Output JSON Format:
        {{
            "form_title": "<string>",
            "form_type": "CONVERSATIONAL",
            "intent_type": "<string>",
            // One of: "sales", "hiring", "partnership", "research", "marketing", "support", "event", "other" — infer from the input.
            "category_context": "<string>",
            // CRITICAL: Copy the user's FULL input here. DO NOT summarize or shorten. This is the most important field.
            "keywords": ["<string>", "..."],
            // What the TARGET AUDIENCE (people the user wants to find) would say directly.
            "implied_keywords": ["<string>", "..."],
            // Problems, situations, frustrations the TARGET AUDIENCE experiences.
            "competitors": ["<string>", "..."],
            // Relevant competitor brands/alternatives in this space.
            "ai_response_guide": "<string>",
            // REQUIRED: A persona/tone description for AI responses. Example: "Respond as a friendly copywriter offering free audit", "Reply as a construction materials sales rep", "Act as a fintech partnership manager". Be specific about role and approach.
            "location": ["<city or region>", "..."],
            // Only if explicitly mentioned or confidently inferred.
            "post_age_filter": "<string>",
            // OPTIONAL: Time range for posts. Extract if user mentions recency: "24h" (last 24 hours), "7d" (last week), "30d" (last month), "3m" (last 3 months), "6m" (last 6 months), "1y" (last year), or "all" (default - no time filter). Only set if user explicitly mentions timeframe like "recent posts", "last week", "past month", etc.
            "buying_signals": ["<string>", "..."],
            // Phrases showing the TARGET AUDIENCE is ready/interested.
            "excluded_keywords": ["<string>", "..."],
            // CRITICAL: Phrases used by people on the OPPOSITE SIDE (the user's competitors/wrong audience type).
            "add_to_history": <boolean>,
            "auto_generate": <boolean>
        }}

        ### Critical Rules:

        1. **category_context**:
           - MUST be the user's FULL input, word-for-word
           - DO NOT shorten to "fitness" or "tech recruiting"
           - This field determines everything else

        2. **Understand Directionality**:
           - If user is SELLING → find BUYERS (people who need/want what they sell)
           - If user is HIRING → find JOB SEEKERS (people looking for work)
           - If user is BUYING → find SELLERS (people offering what they need)
           - If user is RECRUITING PARTNERS → find people seeking partnerships

        3. **excluded_keywords**:
           - Identify who is on the OPPOSITE SIDE
           - List PHRASES (not single words) that the opposite side uses
           - Examples:
             * User hiring → exclude "we're hiring", "looking for a developer", "send me your resume"
             * User selling services → exclude "I offer training", "hire me", "DM for rates"
             * User buying → exclude "looking to buy", "ISO supplier"
           - Use PHRASES: "we're hiring" NOT just "hiring"
           - Use PHRASES: "message me with your resume" NOT just "resume"
           - Be aggressive with exclusions

        4. **keywords & implied_keywords**:
           - Think from the TARGET AUDIENCE perspective
           - What would THEY say? What problems do THEY have?

        """ + AUTOPOPULATE_EXAMPLES + """

        Return a JSON object that accurately reflects the user's intent and will help find their ideal leads.
    """


class LeadServicePrompts(Enum):
    IMPORTED_CONVERSATIONAL_LEAD_ENRICHMENT_PROMPT = """
        You are an AI assistant enriching sales signal data for CRM ingestion.

        You will receive a lead object and must infer the following fields for an ImportedConversationalLeadEnrichmentResponse:

        - summary_of_mention (string | null) — a concise rephrasing of the "mention" field.

        - follow_up_message (string | null) — a short, personalized follow-up message.

        - follow_up_approach (string | null) — best follow-up channel (e.g., "Email", "LinkedIn", "Phone").

        - tags (list[string] | null) — short keywords or labels for categorization.

        Rules:
        - If a field cannot be confidently determined, set it to null (or default per schema).
        - Keep all string responses under 300 characters.
        - Do not invent information not supported by the lead data.

        Return only the structured object in the format defined by the schema.

        ### Input Data:
        {lead}
    """


class LeadFormServicePrompts(Enum):
    SUMMARY_PROMPT = """
        You are a business lead analyst with the ability to identify the ideal customer profile for a business using minimal information.

        You will be given basic data about a business through a form.

        Your task is to create a clear, concise summary that describes:
        - The type of customers the business is most likely targeting.
        - The key needs, problems, or desires these customers have that the business can solve.
        - Any relevant industries, demographics, or contexts where these customers are found.
        - Ensure you list the keyowrds and buying intent provided and format them as a list in the html.
        - Round up with the most likely social media platforms and trending conversations or hashtags to find such customers.
        - Use html to format your output and make it easy to read and follow, because it will be embdedded into a html template.
        - Keep the text under 200 words.

        The summary will be sent to a data entry specialist, who will use it to search social media posts and find conversations relevant to the client’s business.

        Write the summary in simple, easy-to-understand language so the data entry specialist can quickly grasp who the business’s ideal client is.
        Output only the text that will be sent to the data entry specialist.

        Data;
        {data}
    """


class LeadFollowUpMessagePromptEnum(Enum):
    LEAD_CAPTURE = """
        You are an AI assistant helping a business capture leads.
        You are given:
        - Business Information: {business_info}
        - Lead Post: {lead_post}

        Task:
        Generate a concise, professional, and persuasive response to the lead’s post.
        Your response should:
        - Directly address the need expressed in the lead’s post.
        - Clearly present how the business’s product/service solves their problem.
        - Encourage the lead to take the next step (e.g., contact sales, schedule a call, sign up).
        - Sound natural and human, not generic or templated.
        - Must not be more than 2 sentences.

        Output only the message text that the business could send to the lead.
    """


class LazarusPrompt(Enum):
    """Prompts for Lazarus Protocol - Resurrection Signal Detection"""
    
    ANALYZE_BUYING_SIGNALS = """
You are analyzing social media posts/tweets to detect buying signals for the Lazarus Protocol.

Context:
- Person: {contact_name}
- Company: {current_company}
- Industry Keywords: {keywords}
- Signal Types to Detect: {signal_types}

⚠️⚠️⚠️ CRITICAL: SMART BUYING SIGNAL DETECTION ⚠️⚠️⚠️

A "BUYING SIGNAL" = Person shows readiness/interest to PURCHASE a product/service
You MUST distinguish: Is person SELLING (promoting) or BUYING (needing)?

═══════════════════════════════════════════════════════════════════
🎯 THE GOLDEN RULE: INTENT & DIRECTION ANALYSIS
═══════════════════════════════════════════════════════════════════

❌ IGNORE - PROMOTIONAL/OUTBOUND Posts (Person is ADVOCATING/SELLING):
   ├─ Recommending products to others
   │  "You should try X", "Switch to Y", "Check out Z", "I recommend X"
   ├─ Testimonials & endorsements
   │  "I love using X", "X is amazing", "Best tool ever", "Changed my life"
   ├─ Marketing calls-to-action
   │  "Sign up today", "Try it now", "Get started", "Join us", "Limited offer"
   ├─ Promotional comparisons
   │  "X is better than Y", "Why we chose X over Y", "X beats all competitors"
   ├─ Speaking for a company
   │  "We at CompanyX", "Our product Y", "We offer Z", "Check out our tool"
   ├─ Success stories & case studies
   │  "How X helped us 10x revenue", "Thanks to X we achieved Y"

   🔑 KEY: Person is GIVING advice/promoting TO audience (OUTBOUND)

✅ DETECT - BUYER/INBOUND Posts (Person is SEEKING/NEEDING):
   ├─ Asking for recommendations
   │  "What CRM should I use?", "Need suggestions for X", "Anyone recommend Y?"
   ├─ Expressing pain/frustration
   │  "This tool is terrible", "So frustrated with X", "Wasting hours on Y"
   ├─ Actively researching
   │  "Anyone use X? Thoughts?", "Comparing X vs Y", "Evaluating tools"
   ├─ Announcing switches/transitions
   │  "Moving away from X", "Switching from Y to something better"
   ├─ Expressing unmet needs
   │  "Wish there was a tool for X", "Can't find solution for Y"

   🔑 KEY: Person is SEEKING help/expressing need FROM audience (INBOUND)

═══════════════════════════════════════════════════════════════════
📊 LANGUAGE PATTERN ANALYSIS
═══════════════════════════════════════════════════════════════════

PROMOTIONAL INDICATORS (❌):
• Commands: "Try", "Switch to", "Check out", "Sign up", "Use"
• Positive: "love", "amazing", "great", "best", "recommend"
• Marketing: "today", "now", "free", "limited", "get started"
• Questions TO audience: "Want to see?", "Interested in?"

BUYER INDICATORS (✅):
• Questions FROM audience: "Anyone know?", "What do you use?", "Help!"
• Negative emotions: "frustrated", "struggling", "tired of", "hate"
• Research mode: "evaluating", "considering", "comparing", "looking for"
• Pain words: "slow", "buggy", "expensive", "complicated", "broken"

═══════════════════════════════════════════════════════════════════
💡 REAL-WORLD EXAMPLES (Learn from these)
═══════════════════════════════════════════════════════════════════

❌ "Switch to ProductX today - game changer for marketing!"
   Analysis: Imperative command, promotional tone → PROMOTING (IGNORE)

❌ "I've been using ProductX for 6 months - absolute game changer!"
   Analysis: Testimonial, satisfied customer → PROMOTING (IGNORE)

❌ "Are you struggling with lead gen? Try ProductX - we can help"
   Analysis: Marketing pitch with CTA → PROMOTING (IGNORE)

✅ "Anyone have good alternatives to Salesforce? Budget is tight"
   Analysis: Question seeking help + pain point → SEEKING SOLUTION (DETECT "switch")

✅ "Our current marketing tool is so buggy and slow. Drives me crazy!"
   Analysis: Expressing frustration with current solution → PAIN SIGNAL (DETECT "pain")

✅ "Looking for social media management tools - what do you all use?"
   Analysis: Actively researching options → BUYING INTENT (DETECT "switch")

✅ "Thrilled to announce my promotion to VP of Sales at AcmeCorp!"
   Analysis: Career milestone announcement → CAREER CHANGE (DETECT "promoted")

✅ "We're torn between HubSpot and Salesforce. Anyone used both?"
   Analysis: Active evaluation/comparison → DECISION MODE (DETECT "switch")

❌ "Just onboarded 5 clients to ProductX - they're loving it!"
   Analysis: Consultant sharing success → PROMOTING (IGNORE)

Posts to analyze:
{tweets}

Signal Type Definitions (11 Categories):

🎯 CAREER CHANGE SIGNALS (Highest Priority):
- "promoted": Person announces they've been promoted to a new role/title (VP, Director, Manager, etc.)
  Examples: "Excited to announce my promotion to VP of Sales!", "New role alert: Director of Engineering"
- "changed_jobs": Person switched companies or started a new position at a different company
  Examples: "Thrilled to join Acme Corp as Head of Marketing", "Day 1 at my new role"
- "new_decision_maker": Person explicitly mentions they're now responsible for decisions/budget in a relevant area
  Examples: "Now leading our tech stack decisions", "Responsible for vendor selection"

💰 BUSINESS GROWTH SIGNALS (Budget Available):
- "raised_funds": Company announced funding, investment, or capital raise
  Examples: "We raised $10M Series A!", "Excited to announce our seed round"
- "hiring": Company is hiring for roles related to your solution, team expansion
  Examples: "We're hiring 5 engineers!", "Join our growing sales team"
- "expansion": Company announces office expansion, new market entry, or scaling operations
  Examples: "Opening our London office!", "Expanding to APAC region", "Doubled our team size"

😫 PAIN SIGNALS (Active Problem):
- "pain": Expressing frustration, complaints, or problems with current tools/solutions you can solve
  Examples: "Our CRM is so slow", "Wasting hours on manual data entry", "This tool is frustrating"
- "competitor_complaint": Specifically complaining about or expressing dissatisfaction with a competitor's product
  Examples: "Salesforce is too expensive", "HubSpot's UI is confusing", "Tired of [competitor] bugs"

🔥 ENGAGEMENT SIGNALS (Warm/Interested):
- "switch": Actively looking for alternatives, asking for recommendations, considering switching tools
  Examples: "Anyone know a good alternative to X?", "Evaluating new solutions", "Time to switch"
- "likes_competitor": Person likes/engages with competitor posts (requires metadata analysis - detect from context if mentioned)
- "interacts_with_content": Person engages with industry content relevant to your solution

═══════════════════════════════════════════════════════════════════
🎯 CRITICAL: INDUSTRY KEYWORD MATCHING
═══════════════════════════════════════════════════════════════════

USER-PROVIDED KEYWORDS: {keywords}

These keywords define the user's target industry/solution. Use HYBRID TIERED DETECTION:

═══════════════════════════════════════════════════════════════════
🎯 OPTION C: SMART HYBRID DETECTION STRATEGY
═══════════════════════════════════════════════════════════════════

TIER 1 - ALWAYS DETECT (No Keyword Match Required):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Signal Types: promoted, changed_jobs, new_decision_maker, raised_funds, hiring, expansion

Detection Rule: ALWAYS detect these regardless of keywords
Confidence: Set to 0.9 baseline (high priority)
Reasoning: Life events = universal buying opportunities

Examples:
✅ "Promoted to VP of Sales" → DETECT (confidence 0.9) even if keywords = ["accounting"]
✅ "We raised $10M Series A" → DETECT (confidence 0.9) even if keywords = ["CRM"]

TIER 2 - DETECT ALL + KEYWORD SCORING (Keywords Boost Confidence):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Signal Types: pain, competitor_complaint, switch

Detection Rule: Detect ALL genuine pain/switch signals (even without keywords)
Confidence Boost: Add +0.20 if keywords match

Examples with Keywords = ["CRM", "sales automation"]:

1️⃣ Pain + Keyword Match:
   Post: "Our CRM is so slow and buggy"
   Match: ✅ "CRM" exact match
   Base confidence: 0.75
   Keyword boost: +0.20
   Final confidence: 0.95 (CRITICAL PRIORITY)

2️⃣ Pain + No Keyword Match:
   Post: "This project management tool is terrible"
   Match: ❌ None
   Base confidence: 0.75
   Keyword boost: 0
   Final confidence: 0.75 (MEDIUM PRIORITY - still valid buyer)

3️⃣ Switch + Keyword Match:
   Post: "Looking for better sales automation tools"
   Match: ✅ "sales automation" exact match
   Base confidence: 0.75
   Keyword boost: +0.20
   Final confidence: 0.95 (CRITICAL PRIORITY)

4️⃣ Switch + Related Keyword:
   Post: "Need recommendations for managing customer relationships"
   Match: ~ Related to "CRM" (synonym match)
   Base confidence: 0.75
   Keyword boost: +0.15
   Final confidence: 0.90 (HIGH PRIORITY)

CONFIDENCE SCORING FORMULA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Base:
- Career/Growth signals → 0.9 (always high)
- Pain/Switch signals → 0.75 (baseline)

Keyword Boost (only for pain/switch):
+ Exact keyword match → +0.20
+ Synonym match (e.g., "CRM" = "customer relationship management") → +0.15
+ Related match (e.g., "sales tech", "marketing tools") → +0.10
+ Strong pain language ("terrible", "hate", "broken") → +0.05

Maximum: 1.0

KEYWORD MATCHING INTELLIGENCE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Match exact terms, synonyms, and contextual relevance:
- "CRM" matches: "CRM", "customer relationship management", "sales database"
- "sales automation" matches: "sales automation", "sales tech stack", "automating sales"
- "lead generation" matches: "lead generation", "lead gen", "finding prospects"

Task:
Analyze the posts and determine if ANY of the specified signal types are present.

MULTI-FACTOR ANALYSIS CHECKLIST:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. ✅ Does content mention industry keywords or related terms?
2. ✅ Are there career changes, promotions, or new responsibilities?
3. ✅ Are there funding announcements, hiring, or expansion news?
4. ✅ Does it express pain points/frustration relevant to keywords?
5. ✅ Is person asking for recommendations in keyword domain?
6. ✅ Is there indication of budget/buying authority?
7. ✅ Look for EXACT trigger phrases (see detection rules below)
8. ✅ Is this INBOUND (seeking help) vs OUTBOUND (promoting)?

IMPORTANT DETECTION RULES:
- For "promoted": Look for words like "promoted", "new title", "new position", "VP", "Director", "Head of"
- For "changed_jobs": Look for "joining", "new role at", "excited to announce", "day 1 at"
- For "raised_funds": Look for "$", "raised", "funding", "Series A/B/C", "investment", "capital"
- For "hiring": Look for "we're hiring", "join our team", "open positions", "looking for"
- For "expansion": Look for "expanding", "opening", "new office", "scaling", "growing to"
- For "pain": Look for negative emotions: "frustrated", "slow", "broken", "wasting time", "annoying"
- For "competitor_complaint": Look for competitor names + negative words
- For "switch": Look for "alternative", "recommendations", "switching from", "looking for"

Return a JSON object with:
{{
    "signal_detected": boolean,
    "signal_type": "promoted" | "changed_jobs" | "new_decision_maker" | "raised_funds" | "hiring" | "expansion" | "pain" | "competitor_complaint" | "switch" | null,
    "confidence": 0.0 to 1.0,
    "evidence": "exact quote from post that triggered detection",
    "reason": "brief explanation of why this is a buying signal",
    "triggering_post_index": index of the post that triggered this signal (0 for Twitter Post 1, 1 for Twitter Post 2, etc.). Use the post number from the input.
}}

CRITICAL: You MUST provide the "triggering_post_index" field. Look at which post contains the signal:
- Twitter Post 1 → index 0
- Twitter Post 2 → index 1
- LinkedIn Post 1 → index for first LinkedIn (count Twitter posts first)
- LinkedIn Post 2 → next index after first LinkedIn
Example: If you have 3 Twitter posts and 2 LinkedIn posts, and the signal is in "LinkedIn Post 2", the index should be 4 (0,1,2 for Twitter, 3 for LinkedIn Post 1, 4 for LinkedIn Post 2).

Only return TRUE if you have high confidence (>0.7) that this is a genuine buying signal.
"""

    GENERATE_PITCH = """
You are generating a personalized sales pitch for a resurrected lead in the Lazarus Protocol.

Context:
- Contact: {contact_name}
- Current Company: {current_company}
- Alert Type: {alert_type}
- Alert Message: {alert_message}
- Evidence: {evidence}
- Your Business: {business_context}

Task:
Generate a short, personalized pitch (2-3 sentences max) that:
1. References the specific signal detected (job change, pain point, etc.)
2. Shows you understand their situation
3. Offers clear value proposition
4. Includes a soft call-to-action

Tone: Professional, helpful, not salesy. Sound like a human reaching out, not a template.

Example for job change:
"Congrats on the new role at {company}! As you're building out your team, thought our {solution} might be helpful - we've helped similar companies reduce {pain_point} by 40%. Happy to share a quick demo if useful."

Generate the pitch:
"""

    EXTRACT_KEYWORDS_FROM_POST = """
You are extracting industry keywords from a social media post to set up monitoring in the Lazarus Protocol.

Post Content:
{post_content}

Additional Context (if available):
- Bio: {bio}
- Company: {company}
- Job Title: {job_title}
- Signal Types User Cares About: {signal_types}

Task:
Extract 5-8 relevant keywords that would be useful for monitoring this person's activity for buying signals.

Consider:
1. Company names mentioned
2. Technologies, tools, or solutions discussed
3. Industry-specific terms
4. Problems or pain points mentioned
5. Competitor names
6. If user cares about "funding" signals: include investor/VC terms
7. If user cares about "hiring" signals: include role/department terms
8. If user cares about "pain" signals: include problem keywords
9. If user cares about "switch" signals: include alternative/competitor terms

Return a JSON object:
{{
    "keywords": ["keyword1", "keyword2", ...],
    "confidence": 0.0 to 1.0,
    "reasoning": "brief explanation of why these keywords were chosen"
}}

Focus on keywords that will help detect future buying signals, not just describe the current post.
"""
