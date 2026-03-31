from enum import Enum
from app.domain.enums.leadform_autopopulate_examples import AUTOPOPULATE_EXAMPLES
from app.domain.enums.googlemaps_autopopulate_examples import GOOGLE_MAPS_AUTOPOPULATE_EXAMPLES


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
        You are an expert lead generation analyst specialized in person-based lead discovery. A user has described the type of professionals they want to find using Apollo's search platform.

        Your job is to extract COMPLETE search parameters that capture:
        1. **Job titles/roles** (what they do)
        2. **Industry/sector context** (what field they work in)
        3. **Geographic location** (where they are)
        4. **Company characteristics** (size, type, domain)
        5. **Seniority level** (their position in org hierarchy)

        ### User Input:
        {data}

        ### Critical Instructions:

        1. **Extract Industry/Domain Context**:
           - Identify the INDUSTRY or SECTOR mentioned (e.g., "real estate", "fintech", "healthcare", "e-commerce", "SaaS")
           - Add industry keywords to BOTH `q_keywords` AND form_title
           - Examples:
             * "Real estate founders" → q_keywords: "real estate"
             * "Tech startup CTOs" → q_keywords: "technology OR software OR SaaS"
             * "Healthcare executives" → q_keywords: "healthcare OR medical OR hospital"

        2. **Person Titles**:
           - Extract job titles/roles (e.g., "Founder", "CEO", "CTO", "VP Sales")
           - Be specific if user is specific, broad if user is broad
           - Examples:
             * "Real estate founders" → ["Founder", "Co-Founder", "Owner"]
             * "Sales leaders in fintech" → ["VP Sales", "Sales Director", "Head of Sales"]

        3. **Include Similar Titles**:
           - Set to `true` by default to catch variations
           - Set to `false` only if user wants EXACT titles only

        4. **Locations**:
           - Extract cities, states, or countries mentioned
           - Format: ["City, State", "City, Country", "Country"]
           - Examples: ["Lagos, Nigeria"], ["San Francisco, California"], ["United Kingdom"]

        5. **Seniorities**:
           - Map to Apollo seniority levels: "C-Level", "VP", "Director", "Manager", "Senior", "Entry"
           - Examples:
             * "Executives" → ["C-Level", "VP"]
             * "Founders" → ["C-Level"]
             * "Managers" → ["Manager", "Senior"]

        6. **Company Size** (organization_num_employees_ranges):
           - Only include if mentioned or strongly implied
           - Format: ["1,10", "11,50", "51,200", "201,500", "501,1000", "1001,10000", "10001+"]
           - Examples:
             * "startup founders" → ["1,10", "11,50", "51,200"]
             * "enterprise executives" → ["1001,10000", "10001+"]

        7. **q_keywords** (MOST IMPORTANT - REQUIRED):
           - This is THE KEY FIELD that filters by industry/company type/stage
           - ALWAYS include this field when ANY industry, sector, or company type is mentioned
           - Must contain BOTH:
             a) Industry/sector keywords (e.g., "tech", "healthcare", "fintech")
             b) Company type/stage keywords (e.g., "startup", "enterprise", "SME", "scale-up")
           - Use OR to combine related terms
           - Examples:
             * "Tech startups" → "technology OR tech OR software OR IT OR startup OR early stage"
             * "Real estate companies" → "real estate OR property OR housing OR construction OR real estate development"
             * "Fintech scale-ups" → "fintech OR financial services OR banking OR payments OR scale-up OR growth stage"
             * "Enterprise SaaS" → "SaaS OR software OR technology OR cloud OR enterprise"
             * "Healthcare startups" → "healthcare OR medical OR hospital OR health services OR startup OR early stage"

        ### Output Format:
        Return ONLY a valid JSON object:
        {{
            "form_title": "<descriptive title including industry and role>",
            "person_titles": ["<title1>", "<title2>", "..."],
            "include_similar_titles": true,
            "person_locations": ["<location1>", "..."],
            "person_seniorities": ["<seniority1>", "..."],
            "organization_num_employees_ranges": ["<range1>", "..."],
            "q_keywords": "<industry keywords with OR operators>",
            "contact_email_status": ["verified"]
        }}

        ### Examples:

        **Input:** "Real estate founders in Lagos, Nigeria"
        **Output:**
        {{
            "form_title": "Real Estate Founders in Lagos, Nigeria",
            "person_titles": ["Founder", "Co-Founder", "Owner", "CEO"],
            "include_similar_titles": true,
            "person_locations": ["Lagos, Nigeria"],
            "person_seniorities": ["C-Level"],
            "organization_num_employees_ranges": ["1,10", "11,50", "51,200"],
            "q_keywords": "real estate OR property OR housing OR construction OR real estate development",
            "contact_email_status": ["verified"]
        }}

        **Input:** "Tech startup CTOs in Berlin working in fintech"
        **Output:**
        {{
            "form_title": "Fintech Startup CTOs in Berlin",
            "person_titles": ["CTO", "Chief Technology Officer", "VP Engineering"],
            "include_similar_titles": true,
            "person_locations": ["Berlin, Germany"],
            "person_seniorities": ["C-Level", "VP"],
            "organization_num_employees_ranges": ["1,10", "11,50", "51,200"],
            "q_keywords": "fintech OR financial technology OR payments OR banking OR financial services OR startup OR early stage",
            "contact_email_status": ["verified"]
        }}

        **Input:** "Find me startups in Tech space in Nigeria"
        **Output:**
        {{
            "form_title": "Tech Startups in Nigeria",
            "person_titles": ["Founder", "Co-Founder", "CEO", "CTO"],
            "include_similar_titles": true,
            "person_locations": ["Nigeria"],
            "person_seniorities": ["C-Level"],
            "organization_num_employees_ranges": ["1,10", "11,50", "51,200"],
            "q_keywords": "technology OR tech OR software OR IT OR information technology OR startup OR early stage",
            "contact_email_status": ["verified"]
        }}

        **Input:** "Healthcare executives in the US"
        **Output:**
        {{
            "form_title": "Healthcare Executives in United States",
            "person_titles": ["CEO", "COO", "CFO", "President", "Vice President"],
            "include_similar_titles": true,
            "person_locations": ["United States"],
            "person_seniorities": ["C-Level", "VP"],
            "q_keywords": "healthcare OR medical OR hospital OR clinic OR health services OR pharmaceutical",
            "contact_email_status": ["verified"]
        }}

        ### Important Rules:
        - ALWAYS include `q_keywords` when an industry/sector OR company type is mentioned or implied
        - `q_keywords` MUST contain BOTH industry AND company type/stage when both are mentioned
          * "Tech startups" → Include BOTH "tech/software/IT" AND "startup/early stage"
          * "Enterprise SaaS" → Include BOTH "SaaS/software/cloud" AND "enterprise"
          * "Fintech scale-ups" → Include BOTH "fintech/financial services" AND "scale-up/growth stage"
        - Use OR operators in `q_keywords` to catch variations
        - Set `include_similar_titles` to true unless user wants exact matches only
        - Only include fields that are relevant to the user's input
        - Default `contact_email_status` to ["verified"] for best quality leads
    """

    ORGANIZATION_FORM_PROMPT = """
        You are an intelligent B2B marketing assistant specialized in organization-based lead discovery. A user has described their ideal target companies using Apollo's search platform.

        Your job is to extract COMPLETE search parameters that capture:
        1. **Industry/sector** (what type of companies)
        2. **Company size** (employee count, revenue)
        3. **Geographic location** (where they operate)
        4. **Technology stack** (what tools they use)
        5. **Company characteristics** (keywords, tags, attributes)

        ### User Input:
        {data}

        ### Critical Instructions:

        1. **Extract Industry/Sector Keywords** (q_organization_keyword_tags):
           - This is THE MOST IMPORTANT FIELD for filtering by industry AND company type/stage
           - Identify ALL relevant industry/sector terms PLUS company type/stage
           - Must include BOTH:
             a) Industry/sector keywords (e.g., "fintech", "healthcare", "SaaS")
             b) Company type/stage keywords (e.g., "startup", "enterprise", "SME", "scale-up")
           - Include variations, synonyms, and related terms to maximize search coverage
           - Examples:
             * "Real estate companies" → ["real estate", "property", "housing", "construction", "property management"]
             * "Fintech startups" → ["fintech", "financial technology", "payments", "banking", "financial services", "startup", "early stage"]
             * "Healthcare providers" → ["healthcare", "medical", "hospital", "clinic", "health services"]
             * "Tech startups" → ["technology", "tech", "software", "IT", "startup", "early stage", "seed stage"]
             * "Enterprise SaaS" → ["SaaS", "software", "cloud", "technology", "enterprise", "B2B"]
             * "Coworking spaces" → ["coworking", "co-working", "shared workspace", "flexible workspace", "office space", "business center"]
             * "Small businesses" → ["small business", "SME", "small enterprise", "local business"]
             * "FMCG" → ["FMCG", "fast moving consumer goods", "consumer goods", "consumer products", "food and beverage", "personal care", "household products"]
             * "Manufacturing" → ["manufacturing", "industrial", "production", "factory", "fabrication", "assembly"]
             * "Restaurants" → ["restaurant", "dining", "food service", "eatery", "food and beverage", "hospitality"]
             * "Schools" → ["school", "education", "educational institution", "academy", "learning center"]

        2. **Company Locations** (organization_locations):
           - Extract cities, states, regions, or countries
           - Format: ["City, Country"] or ["State, Country"] or ["Country"]
           - **CRITICAL LOCATION RULES**:
             * If ONLY a city name is mentioned that is commonly found in Nigeria (Lagos, Abuja, Port Harcourt, Ibadan, Kano, Ife, Benin, Enugu, etc.), ALWAYS append ", Nigeria"
             * If ONLY a state name is mentioned (Ogun, Lagos State, Rivers, Kano, etc.), ALWAYS append ", Nigeria"
             * For US states (California, Texas, New York, etc.), ALWAYS append ", United States"
             * For other international cities without country, keep as-is if globally unique (e.g., Paris, London, Tokyo)
           - Examples:
             * "Lagos" → ["Lagos, Nigeria"]
             * "Ogun state" → ["Ogun State, Nigeria"]
             * "Abuja" → ["Abuja, Nigeria"]
             * "Ife" → ["Ife, Nigeria"]
             * "California" → ["California, United States"]
             * "United Kingdom" → ["United Kingdom"]

        3. **Company Size** (organization_num_employees_ranges):
           - Extract or infer from descriptors like "startup", "enterprise", "SMB"
           - Format: ["1,10", "11,50", "51,200", "201,500", "501,1000", "1001,10000", "10001+"]
           - Examples:
             * "startups" → ["1,10", "11,50", "51,200"]
             * "mid-market" → ["201,500", "501,1000"]
             * "enterprise" → ["1001,10000", "10001+"]
             * "SMB" or "small business" → ["1,10", "11,50", "51,200"]

        4. **Revenue Range** (revenue_range_min, revenue_range_max):
           - Only if explicitly mentioned
           - Values in millions (USD)
           - Examples:
             * "$1M-$10M ARR" → revenue_range_min: 1, revenue_range_max: 10
             * "At least $5M revenue" → revenue_range_min: 5

        5. **Technology Stack** (technology_uids):
           - Extract specific tools/platforms mentioned
           - Examples: ["Salesforce", "HubSpot", "Stripe", "AWS", "Shopify"]

        6. **Exclude Locations** (organization_not_locations):
           - Only if user explicitly excludes certain locations
           - Format same as organization_locations

        7. **Specific Company Name** (q_organization_name):
           - Only if user mentions a specific company name to search for

        ### Output Format:
        Return ONLY a valid JSON object:
        {{
            "form_title": "<descriptive title including industry and criteria>",
            "organization_locations": ["<location1>", "..."],
            "organization_not_locations": ["<excluded location>", "..."],
            "organization_num_employees_ranges": ["<range1>", "..."],
            "revenue_range_min": <number or null>,
            "revenue_range_max": <number or null>,
            "technology_uids": ["<tech1>", "..."],
            "q_organization_keyword_tags": ["<keyword1>", "<keyword2>", "..."],
            "q_organization_name": "<company name or null>"
        }}

        ### Examples:

        **Input:** "Real estate companies in Lagos, Nigeria"
        **Output:**
        {{
            "form_title": "Real Estate Companies in Lagos, Nigeria",
            "organization_locations": ["Lagos, Nigeria"],
            "organization_num_employees_ranges": ["1,10", "11,50", "51,200", "201,500"],
            "q_organization_keyword_tags": ["real estate", "property", "housing", "construction", "property management", "real estate development"]
        }}

        **Input:** "Fintech startups in San Francisco with at least $5M revenue"
        **Output:**
        {{
            "form_title": "Fintech Startups in San Francisco ($5M+ Revenue)",
            "organization_locations": ["San Francisco, California"],
            "organization_num_employees_ranges": ["1,10", "11,50", "51,200"],
            "revenue_range_min": 5,
            "q_organization_keyword_tags": ["fintech", "financial technology", "payments", "banking", "financial services", "payment processing", "startup", "early stage"]
        }}

        **Input:** "Tech startups in Nigeria"
        **Output:**
        {{
            "form_title": "Tech Startups in Nigeria",
            "organization_locations": ["Nigeria"],
            "organization_num_employees_ranges": ["1,10", "11,50", "51,200"],
            "q_organization_keyword_tags": ["technology", "tech", "software", "IT", "information technology", "startup", "early stage", "seed stage"]
        }}

        **Input:** "Mid-market SaaS companies using Salesforce"
        **Output:**
        {{
            "form_title": "Mid-Market SaaS Companies Using Salesforce",
            "organization_num_employees_ranges": ["201,500", "501,1000"],
            "technology_uids": ["Salesforce"],
            "q_organization_keyword_tags": ["SaaS", "software", "cloud", "technology", "software as a service", "mid-market", "growth stage"]
        }}

        **Input:** "Healthcare providers in the US, excluding California"
        **Output:**
        {{
            "form_title": "Healthcare Providers in US (Excluding California)",
            "organization_locations": ["United States"],
            "organization_not_locations": ["California, United States"],
            "q_organization_keyword_tags": ["healthcare", "medical", "hospital", "clinic", "health services", "medical services"]
        }}

        **Input:** "E-commerce companies in Europe"
        **Output:**
        {{
            "form_title": "E-commerce Companies in Europe",
            "organization_locations": ["United Kingdom", "Germany", "France", "Netherlands", "Spain", "Italy"],
            "q_organization_keyword_tags": ["e-commerce", "ecommerce", "online retail", "retail", "online shopping", "marketplace"]
        }}

        **Input:** "Find coworking spaces in Lagos"
        **Output:**
        {{
            "form_title": "Coworking Spaces in Lagos, Nigeria",
            "organization_locations": ["Lagos, Nigeria"],
            "q_organization_keyword_tags": ["coworking", "co-working", "coworking space", "shared workspace", "flexible workspace", "office space", "business center"]
        }}

        **Input:** "Find small businesses in Lagos"
        **Output:**
        {{
            "form_title": "Small Businesses in Lagos, Nigeria",
            "organization_locations": ["Lagos, Nigeria"],
            "organization_num_employees_ranges": ["1,10", "11,50"],
            "q_organization_keyword_tags": ["small business", "SME", "small enterprise", "local business"]
        }}

        **Input:** "Find FMCGs in Lagos"
        **Output:**
        {{
            "form_title": "FMCG Companies in Lagos, Nigeria",
            "organization_locations": ["Lagos, Nigeria"],
            "q_organization_keyword_tags": ["FMCG", "fast moving consumer goods", "consumer goods", "consumer products", "food and beverage", "personal care", "household products", "packaged goods"]
        }}

        **Input:** "Find manufacturing companies in Ogun state"
        **Output:**
        {{
            "form_title": "Manufacturing Companies in Ogun State, Nigeria",
            "organization_locations": ["Ogun State, Nigeria"],
            "q_organization_keyword_tags": ["manufacturing", "industrial", "production", "factory", "fabrication", "assembly"]
        }}

        **Input:** "Find restaurants in Abuja"
        **Output:**
        {{
            "form_title": "Restaurants in Abuja, Nigeria",
            "organization_locations": ["Abuja, Nigeria"],
            "q_organization_keyword_tags": ["restaurant", "dining", "food service", "eatery", "food and beverage", "hospitality"]
        }}

        **Input:** "Find secondary schools in Ife"
        **Output:**
        {{
            "form_title": "Secondary Schools in Ife, Nigeria",
            "organization_locations": ["Ife, Nigeria"],
            "q_organization_keyword_tags": ["secondary school", "high school", "education", "school", "educational institution", "private school", "boarding school"]
        }}

        ### Important Rules:
        - ALWAYS include `q_organization_keyword_tags` with industry/sector AND company type/stage keywords
        - `q_organization_keyword_tags` MUST contain BOTH industry AND company type when both are mentioned
          * "Tech startups" → Include BOTH "tech/software/IT" AND "startup/early stage"
          * "Enterprise SaaS" → Include BOTH "SaaS/software/cloud" AND "enterprise"
          * "Fintech scale-ups" → Include BOTH "fintech/financial services" AND "scale-up/growth stage"
        - Include multiple variations and related terms in keyword tags for better search coverage
        - **LOCATION DEFAULTS**: When user mentions only a city/state name commonly found in Nigeria (Lagos, Abuja, Ogun, Ife, Port Harcourt, Ibadan, Kano, etc.) WITHOUT specifying a country, ALWAYS default to Nigeria
          * "Lagos" → "Lagos, Nigeria"
          * "Ogun state" → "Ogun State, Nigeria"
          * "Ife" → "Ife, Nigeria"
        - **STATE REQUIREMENT**: When user mentions only a state name (e.g., "Ogun state", "California"), ALWAYS append the country
          * "Ogun state" → "Ogun State, Nigeria"
          * "California" → "California, United States"
        - For ambiguous international cities (e.g., "Paris", "London"), keep as-is unless context suggests otherwise
        - Only include fields that are relevant to the user's input
        - When user says "startups" or "small business", include appropriate employee ranges: ["1,10", "11,50", "51,200"]
        - When user says "enterprise", use larger employee ranges: ["1001,10000", "10001+"]
        - Use descriptive form titles that capture the search criteria
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

    GOOGLE_MAPS_FORM_PROMPT = """
        You are an expert local business discovery assistant with advanced query disambiguation capabilities.

        Your task is to interpret user queries (which may be ambiguous or use acronyms) and generate precise Google Maps search parameters.

        ### CRITICAL: Handle Ambiguous Queries
        - Detect acronyms (POS, ATM, PC, AI, etc.) and expand them contextually
        - Use location and context clues to disambiguate
        - Add synonyms and related terms to improve search accuracy
        - Include excluded_terms to filter out wrong matches

        ### User Input:
        {data}

        Return a JSON object optimized for Google Maps search with enhanced context:
        {{
            "form_title": "<string>",
            "maps_search_mode": "text",
            // Usually "text" for natural language queries
            "maps_search_query": "<string>",
            // EXPANDED query with synonyms and full forms
            // Example: "POS" → "Point of Sale agents, mobile money agents, POS terminals"
            // Example: "restaurants" → "restaurants, dining, eateries, food establishments"
            "maps_location": "<string>",
            // City, neighborhood, or address with country
            "maps_latitude": <number or null>,
            // Only if user provides exact coordinates
            "maps_longitude": <number or null>,
            // Only if user provides exact coordinates
            "maps_radius_km": <number>,
            // Default: 5km for cities, 10km for large metros
            "maps_business_types": ["<type>", "..."],
            // Google Places types - use appropriate ones for industry
            "maps_min_rating": <number>,
            // 3.0 default, 4.0+ for "good/best", 3.5 for quality
            "maps_exclude_closed": true,
            // Usually true
            "maps_max_results": <number>,
            // 20-40 typical
            "business_context": "<string>",
            // NEW: Describe the business type/industry for clarity
            "excluded_terms": ["<term>", "..."]
            // NEW: Terms to exclude from results (handle ambiguity)
        }}

        """ + GOOGLE_MAPS_AUTOPOPULATE_EXAMPLES + """

        ### Instructions:
        1. ALWAYS expand ambiguous terms and acronyms
        2. Add industry-specific synonyms to maps_search_query
        3. Use business_context to describe what user is looking for
        4. Add excluded_terms for ambiguous queries
        5. Set appropriate filters based on quality hints

        Return only the JSON object that accurately reflects the user's search intent with full context expansion.
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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️⚠️⚠️ CRITICAL: DEEP CONTEXTUAL ANALYSIS REQUIRED ⚠️⚠️⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

YOU MUST READ THE **ENTIRE** POST FROM START TO FINISH BEFORE MAKING ANY DECISION.

❌ DO NOT just scan for trigger words and assume
❌ DO NOT base decision on one sentence out of context
❌ DO NOT detect "pain" if the full post shows it's resolved/positive
❌ DO NOT detect "switch" if person is recommending TO others (not seeking FOR themselves)

✅ YOU MUST analyze the FULL context:
   1. Read the complete post - every sentence matters
   2. Understand the overall sentiment and direction (INBOUND vs OUTBOUND)
   3. Consider what comes BEFORE and AFTER trigger words
   4. Verify the person is actually experiencing the pain/need, not just mentioning it

CONTEXTUAL ANALYSIS EXAMPLES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Example 1 - FALSE POSITIVE (Read Full Context):
❌ WRONG: "I see 'frustrated' → DETECT pain"
✅ CORRECT Analysis:
   Post: "I used to be frustrated with slow CRMs, but after switching to HubSpot, everything is smooth!"
   Trigger word: "frustrated" (appears in post)
   Full context: Past tense pain that's ALREADY RESOLVED
   Decision: REJECT - No current pain, this is a success story/testimonial

Example 2 - MISSING CONTEXT (Read Entire Post):
❌ WRONG: "I see 'switch to' → DETECT switch signal"
✅ CORRECT Analysis:
   Post: "If you're still using spreadsheets for CRM, you should switch to a proper platform. We made the switch 2 years ago and never looked back!"
   Trigger phrase: "switch to" (appears in post)
   Full context: Person is RECOMMENDING others switch (OUTBOUND), not seeking to switch themselves
   Decision: REJECT - Promotional advice, not buyer intent

Example 3 - PARTIAL SENTENCE TRAP:
❌ WRONG: "I see 'slow' and 'CRM' → DETECT pain"
✅ CORRECT Analysis:
   Post: "Just helped a client move from their slow CRM to Salesforce. Impressive results!"
   Trigger words: "slow" + "CRM" (both appear)
   Full context: Consultant talking about CLIENT'S problem (3rd party), not their own
   Decision: REJECT - Not expressing personal pain, talking about others

Example 4 - GENUINE SIGNAL (Correct Detection):
✅ CORRECT Analysis:
   Post: "Our CRM is painfully slow. Takes 5 minutes to load a contact. Evaluating alternatives - anyone have recommendations?"
   Trigger words: "slow", "alternatives", "recommendations"
   Full context: Person expressing CURRENT pain + ACTIVELY seeking solutions (INBOUND)
   Decision: DETECT "switch" - High confidence (0.95)

MULTI-FACTOR ANALYSIS CHECKLIST (Apply AFTER Reading Full Post):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. ✅ Read ENTIRE post first - understand full context
2. ✅ Verify person is expressing THEIR OWN need (not talking about clients/others)
3. ✅ Check if pain/need is CURRENT (not past/resolved)
4. ✅ Confirm direction: INBOUND (seeking help) vs OUTBOUND (giving advice)
5. ✅ Ensure keywords appear in context of genuine need, not promotional mention
6. ✅ Verify career changes are NEW announcements (not historical)
7. ✅ Check funding/hiring/expansion are CURRENT events (not old news)
8. ✅ Confirm switch signals show ACTIVE evaluation (not recommendations to others)

TRIGGER PHRASE DETECTION (Only After Full Context Check):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- "promoted": NEW promotion announcement (not historical: "when I was promoted 3 years ago")
- "changed_jobs": RECENT job change (not "I changed jobs last year and...")
- "raised_funds": CURRENT funding announcement (not "we raised funds in 2020")
- "hiring": ACTIVE hiring (not "we were hiring but filled the roles")
- "expansion": ONGOING expansion (not "we expanded last quarter")
- "pain": CURRENT frustration THEY are experiencing (not resolved/past/others' pain)
- "competitor_complaint": THEIR dissatisfaction (not reporting what others say)
- "switch": ACTIVELY seeking alternatives FOR THEMSELVES (not advising others)

Return a JSON object with:
{{
    "signal_detected": boolean,
    "signal_type": "promoted" | "changed_jobs" | "new_decision_maker" | "raised_funds" | "hiring" | "expansion" | "pain" | "competitor_complaint" | "switch" | null,
    "confidence": 0.0 to 1.0,
    "evidence": "exact quote from post that triggered detection",
    "reason": "brief explanation of why this is a buying signal",
    "triggering_post_index": index of the post that triggered this signal (0 for Twitter Post 1, 1 for Twitter Post 2, etc.). Use the post number from the input,
    "rejection_reason": "REQUIRED when signal_detected=false: Human-friendly explanation of why posts didn't qualify (e.g., 'Posts are promotional content, not buying signals', 'No career changes or pain points detected', 'Posts don't relate to target keywords: CRM, sales automation')"
}}

CRITICAL: You MUST provide the "triggering_post_index" field. Look at which post contains the signal:
- Twitter Post 1 → index 0
- Twitter Post 2 → index 1
- LinkedIn Post 1 → index for first LinkedIn (count Twitter posts first)
- LinkedIn Post 2 → next index after first LinkedIn
Example: If you have 3 Twitter posts and 2 LinkedIn posts, and the signal is in "LinkedIn Post 2", the index should be 4 (0,1,2 for Twitter, 3 for LinkedIn Post 1, 4 for LinkedIn Post 2).

REJECTION REASON EXAMPLES (when signal_detected=false):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Good: "All posts are promotional/marketing content recommending products to others. No genuine buyer intent detected."
✅ Good: "Posts contain general industry updates but no career changes, pain points, or switch signals."
✅ Good: "Content doesn't match target keywords (CRM, sales automation). Posts discuss project management instead."
✅ Good: "Confidence score 0.65 - below 0.70 threshold. Weak pain signal detected but not strong enough."
✅ Good: "Posts are endorsements and testimonials (OUTBOUND). Person is promoting, not seeking solutions."

❌ Bad: "No signal"
❌ Bad: "Doesn't match"
❌ Bad: "Low confidence"

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
