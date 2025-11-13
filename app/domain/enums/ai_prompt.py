from enum import Enum


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
        You are a search term generation and social listening assistant. A user has described what they want to find or monitor online. Your job is to extract intent-agnostic, high-quality search parameters that can be used across any use case (e.g., sales, hiring, partnership, research, marketing, events).

        Based on the user's description, return structured parameters to populate a Conversational Lead form for tracking relevant social media discussions.

        ### User Input:
        {data}

        ### Output JSON (intent-agnostic):
        {{
            "form_title": "<string>",
            "form_type": "CONVERSATIONAL",
            "intent_type": "<string>",  
            // One of: "sales", "hiring", "partnership", "research", "marketing", "support", "event", "other" — infer from the input.
            "keywords": ["<string>", "..."],
            "competitors": ["<string>", "..."],
            "ai_response_guide": "<string>",
            "location": ["<city or region>", "..."],  
            // Only include if explicitly specified or confidently inferred.
            "buying_signals": ["<string>", "..."],  
            // Optional; use when the user implies interest or intent cues relevant to their goal.
            "excluded_keywords": ["<string>", "..."] ,
            "add_to_history": <boolean>,
            "auto_generate": <boolean>
        }}

        ### Rules:
        - Keep keywords concise and specific; avoid overly generic terms (e.g., "news", "content").
        - Include obvious synonyms or related phrases if they improve coverage.
        - Prefer named entities (brands, products, roles, technologies) when relevant.
        - Deduplicate entries; do not include repeated values.
        - Do not bias toward any single scenario (e.g., hiring or sales) unless the user clearly indicates it.
        - If the intent is ambiguous, set "intent_type" to "other" and focus on strong keywords.

        The JSON above is a guide; always return an object that reflects the user's preferences and is optimized for effective conversation tracking.
        Populate location only when specified or confidently inferred from the request.
    """


class LeadServicePrompts(Enum):
    IMPORTED_CONVERSATIONAL_LEAD_ENRICHMENT_PROMPT = """
        You are an AI assistant enriching conversational lead data for CRM ingestion.

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
