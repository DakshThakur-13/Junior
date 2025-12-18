-- ===========================================
-- Junior - Demo Data for Database
-- ===========================================

-- ============ Demo Users ============
INSERT INTO users (id, email, name, role, bar_council_id, preferred_language, subscription_tier, settings, is_active) VALUES
('550e8400-e29b-41d4-a716-446655440001', 'advocate.sharma@example.com', 'Adv. Rajesh Sharma', 'lawyer', 'BAR/DL/2015/12345', 'ENGLISH', 'pro', 
 '{"theme": "dark", "notifications": true, "auto_translate": true, "preferred_courts": ["SUPREME_COURT", "HIGH_COURT"]}', true),
('550e8400-e29b-41d4-a716-446655440002', 'adv.priya@example.com', 'Adv. Priya Menon', 'lawyer', 'BAR/KA/2018/67890', 'HINDI', 'enterprise',
 '{"theme": "light", "notifications": true, "auto_translate": false, "preferred_courts": ["HIGH_COURT", "DISTRICT_COURT"]}', true),
('550e8400-e29b-41d4-a716-446655440003', 'student.kumar@example.com', 'Amit Kumar', 'student', NULL, 'ENGLISH', 'free',
 '{"theme": "light", "notifications": true, "auto_translate": false, "preferred_courts": ["SUPREME_COURT"]}', true)
ON CONFLICT (id) DO NOTHING;

-- ============ Landmark Supreme Court Cases ============
INSERT INTO documents (id, title, court, case_number, case_type, judgment_date, judges, bench_strength, parties, summary, legal_status, keywords, legal_provisions, is_landmark) VALUES

-- 1. Kesavananda Bharati Case (Basic Structure Doctrine)
('650e8400-e29b-41d4-a716-446655440001',
 'Kesavananda Bharati Sripadagalvaru vs State Of Kerala',
 'SUPREME_COURT',
 'Writ Petition (Civil) 135 of 1970',
 'WRIT',
 '1973-04-24',
 ARRAY['Justice S.M. Sikri', 'Justice J.M. Shelat', 'Justice A.N. Grover', 'Justice P. Jaganmohan Reddy', 'Justice H.R. Khanna', 'Justice A.N. Ray', 'Justice K.S. Hegde', 'Justice D.G. Palekar', 'Justice K.K. Mathew', 'Justice M.H. Beg', 'Justice S.N. Dwivedi', 'Justice Y.V. Chandrachud', 'Justice A.K. Mukherjea'],
 13,
 '{"petitioner": ["Kesavananda Bharati"], "respondent": ["State of Kerala"], "advocates": {"petitioner": ["N.A. Palkhivala"], "respondent": ["Attorney General"]}}',
 'Landmark judgment establishing the Basic Structure doctrine, limiting Parliament''s power to amend the Constitution. The Supreme Court held that while Parliament has wide powers to amend the Constitution, it cannot alter its basic structure.',
 'GOOD_LAW',
 ARRAY['basic structure', 'constitutional amendment', 'article 368', 'fundamental rights', 'kesavananda bharati'],
 ARRAY['Article 368', 'Article 13', 'Article 32', 'Part III'],
 true),

-- 2. Maneka Gandhi vs Union of India (Right to Life)
('650e8400-e29b-41d4-a716-446655440002',
 'Maneka Gandhi vs Union Of India',
 'SUPREME_COURT',
 'Writ Petition (Civil) 314 of 1976',
 'WRIT',
 '1978-01-25',
 ARRAY['Justice M.H. Beg', 'Justice Y.V. Chandrachud', 'Justice V.R. Krishna Iyer', 'Justice P.N. Bhagwati', 'Justice N.L. Untwalia'],
 5,
 '{"petitioner": ["Maneka Gandhi"], "respondent": ["Union of India"], "advocates": {"petitioner": ["Shanti Bhushan"], "respondent": ["L.N. Sinha"]}}',
 'Expanded interpretation of Article 21 - Right to Life and Personal Liberty. The Court held that the right to life includes the right to live with dignity and covers various other rights including right to travel abroad.',
 'GOOD_LAW',
 ARRAY['article 21', 'personal liberty', 'right to life', 'passport', 'maneka gandhi'],
 ARRAY['Article 21', 'Article 14', 'Article 19'],
 true),

-- 3. Vishaka vs State of Rajasthan (Sexual Harassment)
('650e8400-e29b-41d4-a716-446655440003',
 'Vishaka And Others vs State Of Rajasthan',
 'SUPREME_COURT',
 'Writ Petition (Criminal) 666-70 of 1992',
 'WRIT',
 '1997-08-13',
 ARRAY['Justice J.S. Verma', 'Justice Sujata V. Manohar', 'Justice B.N. Kirpal'],
 3,
 '{"petitioner": ["Vishaka", "Others"], "respondent": ["State of Rajasthan"], "advocates": {"petitioner": ["Indira Jaising"], "respondent": ["Solicitor General"]}}',
 'Landmark judgment on sexual harassment at workplace. The Supreme Court laid down Vishaka Guidelines to be followed by all workplaces until legislation is enacted.',
 'GOOD_LAW',
 ARRAY['sexual harassment', 'workplace', 'vishaka guidelines', 'women rights', 'article 21'],
 ARRAY['Article 21', 'Article 14', 'Article 15', 'Article 19(1)(g)'],
 true),

-- 4. K.S. Puttaswamy vs Union of India (Right to Privacy)
('650e8400-e29b-41d4-a716-446655440004',
 'Justice K.S. Puttaswamy (Retd.) vs Union Of India',
 'SUPREME_COURT',
 'Writ Petition (Civil) 494 of 2012',
 'WRIT',
 '2017-08-24',
 ARRAY['Justice J.S. Khehar', 'Justice S.A. Bobde', 'Justice R.K. Agrawal', 'Justice R.F. Nariman', 'Justice A.M. Sapre', 'Justice D.Y. Chandrachud', 'Justice S.K. Kaul', 'Justice S. Abdul Nazeer', 'Justice R. Banumathi'],
 9,
 '{"petitioner": ["K.S. Puttaswamy"], "respondent": ["Union of India"], "advocates": {"petitioner": ["Shyam Divan"], "respondent": ["Attorney General K.K. Venugopal"]}}',
 'Nine-judge bench unanimously declared Right to Privacy as a fundamental right under Article 21. This judgment overruled the M.P. Sharma and Kharak Singh precedents.',
 'GOOD_LAW',
 ARRAY['right to privacy', 'fundamental right', 'article 21', 'aadhaar', 'puttaswamy'],
 ARRAY['Article 21', 'Article 14', 'Article 19'],
 true),

-- 5. Shreya Singhal vs Union of India (Section 66A IT Act)
('650e8400-e29b-41d4-a716-446655440005',
 'Shreya Singhal vs Union Of India',
 'SUPREME_COURT',
 'Writ Petition (Criminal) 167 of 2012',
 'WRIT',
 '2015-03-24',
 ARRAY['Justice J. Chelameswar', 'Justice R.F. Nariman'],
 2,
 '{"petitioner": ["Shreya Singhal"], "respondent": ["Union of India"], "advocates": {"petitioner": ["Sanjay Hegde", "Apar Gupta"], "respondent": ["P.P. Malhotra"]}}',
 'Struck down Section 66A of the IT Act, 2000 as unconstitutional for being vague and arbitrary. The Court held that freedom of speech and expression applies to the internet.',
 'GOOD_LAW',
 ARRAY['section 66a', 'information technology act', 'freedom of speech', 'internet freedom', 'shreya singhal'],
 ARRAY['Section 66A IT Act', 'Article 19(1)(a)', 'Article 19(2)', 'Article 21'],
 true),

-- 6. Navtej Singh Johar vs Union of India (Section 377)
('650e8400-e29b-41d4-a716-446655440006',
 'Navtej Singh Johar vs Union Of India',
 'SUPREME_COURT',
 'Writ Petition (Criminal) 76 of 2016',
 'WRIT',
 '2018-09-06',
 ARRAY['Justice Dipak Misra', 'Justice A.M. Khanwilkar', 'Justice R.F. Nariman', 'Justice D.Y. Chandrachud', 'Justice Indu Malhotra'],
 5,
 '{"petitioner": ["Navtej Singh Johar", "Others"], "respondent": ["Union of India"], "advocates": {"petitioner": ["Arvind Datar", "Mukul Rohatgi", "Menaka Guruswamy"], "respondent": ["Tushar Mehta"]}}',
 'Decriminalized consensual homosexual acts by reading down Section 377 of IPC. The judgment upheld the right to sexual autonomy and dignity of LGBTQ+ individuals.',
 'GOOD_LAW',
 ARRAY['section 377', 'lgbtq rights', 'sexual orientation', 'dignity', 'navtej johar'],
 ARRAY['Section 377 IPC', 'Article 21', 'Article 14', 'Article 15', 'Article 19'],
 true),

-- 7. Indian Young Lawyers Association vs State of Kerala (Sabarimala)
('650e8400-e29b-41d4-a716-446655440007',
 'Indian Young Lawyers Association vs State Of Kerala',
 'SUPREME_COURT',
 'Writ Petition (Civil) 373 of 2006',
 'WRIT',
 '2018-09-28',
 ARRAY['Justice Dipak Misra', 'Justice A.M. Khanwilkar', 'Justice R.F. Nariman', 'Justice D.Y. Chandrachud', 'Justice Indu Malhotra'],
 5,
 '{"petitioner": ["Indian Young Lawyers Association"], "respondent": ["State of Kerala"], "advocates": {"petitioner": ["Nalin Kohli"], "respondent": ["K. Parasaran"]}}',
 'Allowed entry of women of all ages into Sabarimala temple, striking down the traditional practice of barring women aged 10-50. The Court held that religious practices must yield to constitutional morality.',
 'GOOD_LAW',
 ARRAY['sabarimala', 'women entry', 'religious freedom', 'article 25', 'gender equality'],
 ARRAY['Article 25', 'Article 26', 'Article 14', 'Article 15', 'Article 17'],
 true)

ON CONFLICT (id) DO NOTHING;

-- ============ Document Chunks with Sample Embeddings ============
-- Note: In production, these embeddings would be generated by your embedding service
-- For demo, we'll insert chunks without embeddings (they can be generated later)

INSERT INTO document_chunks (id, document_id, content, page_number, paragraph_number, chunk_type, token_count) VALUES

-- Kesavananda Bharati chunks
('750e8400-e29b-41d4-a716-446655440001', '650e8400-e29b-41d4-a716-446655440001',
 'The Constitution is not a mere political document. It is the vehicle of life of a nation and its soul. It is a living organism capable of growth and development.',
 1, 1, 'quote', 150),

('750e8400-e29b-41d4-a716-446655440002', '650e8400-e29b-41d4-a716-446655440001',
 'While Parliament has wide powers to amend the Constitution under Article 368, it cannot alter the basic structure or framework of the Constitution. This includes the supremacy of the Constitution, republican and democratic form of government, secular character, separation of powers, and federal character.',
 45, 23, 'paragraph', 220),

-- Maneka Gandhi chunks
('750e8400-e29b-41d4-a716-446655440003', '650e8400-e29b-41d4-a716-446655440002',
 'Article 21 cannot be construed narrowly. The right to life is not merely a physical right but includes the right to live with human dignity and all that goes along with it, namely, the bare necessities of life such as adequate nutrition, clothing, shelter, facilities for reading, writing and expressing oneself.',
 12, 8, 'paragraph', 250),

('750e8400-e29b-41d4-a716-446655440004', '650e8400-e29b-41d4-a716-446655440002',
 'The procedure established by law must be just, fair and reasonable, not arbitrary, fanciful or oppressive. Otherwise, it would be no procedure at all and the requirement of Article 21 would not be satisfied.',
 15, 12, 'paragraph', 180),

-- Vishaka chunks
('750e8400-e29b-41d4-a716-446655440005', '650e8400-e29b-41d4-a716-446655440003',
 'Sexual harassment of a woman at workplace is a violation of the fundamental rights of a woman under Articles 14, 15, 19(1)(g) and 21 of the Constitution of India. It is a form of gender-based violence.',
 8, 5, 'paragraph', 160),

-- Privacy judgment chunks
('750e8400-e29b-41d4-a716-446655440006', '650e8400-e29b-41d4-a716-446655440004',
 'Privacy is a constitutionally protected right which emerges primarily from the guarantee of life and personal liberty in Article 21 of the Constitution. Elements of privacy also arise in varying contexts from the other facets of freedom and dignity recognized and guaranteed by the fundamental rights contained in Part III.',
 234, 156, 'paragraph', 280),

-- Section 66A chunks
('750e8400-e29b-41d4-a716-446655440007', '650e8400-e29b-41d4-a716-446655440005',
 'Section 66A of the IT Act is unconstitutional also on the ground that it takes away the guaranteed freedom under Article 19(1)(a) by a procedure which is not prescribed under Article 19(2). The section is vague and has a chilling effect on free speech.',
 18, 11, 'paragraph', 200)

ON CONFLICT (id) DO NOTHING;

-- ============ Citations (Case Relationships) ============
INSERT INTO citations (citing_document_id, cited_document_id, citation_type, citation_strength, is_binding, paragraph_in_citing) VALUES

-- Puttaswamy (Privacy) follows Maneka Gandhi
('650e8400-e29b-41d4-a716-446655440004', '650e8400-e29b-41d4-a716-446655440002', 'FOLLOWS', 'STRONG', true, 145),

-- Puttaswamy refers to Kesavananda Bharati (Basic Structure)
('650e8400-e29b-41d4-a716-446655440004', '650e8400-e29b-41d4-a716-446655440001', 'REFERS', 'STRONG', true, 89),

-- Shreya Singhal follows Maneka Gandhi
('650e8400-e29b-41d4-a716-446655440005', '650e8400-e29b-41d4-a716-446655440002', 'FOLLOWS', 'STRONG', true, 22),

-- Navtej Johar follows Puttaswamy (Privacy)
('650e8400-e29b-41d4-a716-446655440006', '650e8400-e29b-41d4-a716-446655440004', 'FOLLOWS', 'STRONG', true, 67),

-- Sabarimala refers to Kesavananda (Basic Structure)
('650e8400-e29b-41d4-a716-446655440007', '650e8400-e29b-41d4-a716-446655440001', 'REFERS', 'MEDIUM', true, 34),

-- Sabarimala follows Puttaswamy
('650e8400-e29b-41d4-a716-446655440007', '650e8400-e29b-41d4-a716-446655440004', 'FOLLOWS', 'STRONG', true, 89)

ON CONFLICT ON CONSTRAINT unique_citation DO NOTHING;

-- ============ Demo Chat Sessions ============
INSERT INTO chat_sessions (id, user_id, title, session_type, messages_count, case_context) VALUES

('850e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440001',
 'Research: Right to Privacy Cases', 'RESEARCH', 5,
 '{"case_type": "CONSTITUTIONAL", "keywords": ["privacy", "article 21", "fundamental rights"]}'),

('850e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440002',
 'Drafting: Writ Petition under Article 226', 'DRAFTING', 8,
 '{"court": "HIGH_COURT", "article": "226", "subject": "environmental law"}}')

ON CONFLICT (id) DO NOTHING;

-- ============ Sample Chat Messages ============
INSERT INTO chat_messages (session_id, role, content, citations, token_count, model_used) VALUES

('850e8400-e29b-41d4-a716-446655440001', 'USER',
 'What are the key Supreme Court judgments on Right to Privacy?',
 '[]', 45, NULL),

('850e8400-e29b-41d4-a716-446655440001', 'ASSISTANT',
 'The landmark judgment on Right to Privacy is Justice K.S. Puttaswamy (Retd.) vs Union of India (2017), where a 9-judge bench unanimously declared privacy as a fundamental right under Article 21. The Court held that privacy includes: 1) Personal autonomy, 2) Informational self-determination, 3) Right to be let alone. This judgment overruled earlier decisions and has been followed in subsequent cases like the Aadhaar judgment.',
 '[{"document_id": "650e8400-e29b-41d4-a716-446655440004", "page": 234, "relevance": 0.95}]',
 380, 'llama-3.3-70b-versatile'),

('850e8400-e29b-41d4-a716-446655440001', 'USER',
 'Which earlier cases did Puttaswamy rely on?',
 '[]', 35, NULL),

('850e8400-e29b-41d4-a716-446655440001', 'ASSISTANT',
 'The Puttaswamy judgment extensively relied on Maneka Gandhi vs Union of India (1978), which expanded the interpretation of Article 21. The Court also referred to the Basic Structure doctrine from Kesavananda Bharati (1973) and international privacy jurisprudence.',
 '[{"document_id": "650e8400-e29b-41d4-a716-446655440002", "page": 12, "relevance": 0.92}, {"document_id": "650e8400-e29b-41d4-a716-446655440001", "page": 45, "relevance": 0.88}]',
 290, 'llama-3.3-70b-versatile')

ON CONFLICT (id) DO NOTHING;

-- ============ Update document citation counts ============
UPDATE documents SET 
    cited_by_count = (SELECT COUNT(*) FROM citations WHERE cited_document_id = documents.id),
    citations_count = (SELECT COUNT(*) FROM citations WHERE citing_document_id = documents.id);

-- ============ Update chat session message counts ============
UPDATE chat_sessions SET
    messages_count = (SELECT COUNT(*) FROM chat_messages WHERE session_id = chat_sessions.id);

-- ============ Success Message ============
DO $$
BEGIN
    RAISE NOTICE '===========================================';
    RAISE NOTICE 'Demo data inserted successfully!';
    RAISE NOTICE '===========================================';
    RAISE NOTICE 'Created:';
    RAISE NOTICE '  - 3 demo users (lawyer, student)';
    RAISE NOTICE '  - 7 landmark Supreme Court cases';
    RAISE NOTICE '  - 7 document chunks with content';
    RAISE NOTICE '  - 6 case citations showing relationships';
    RAISE NOTICE '  - 2 chat sessions with messages';
    RAISE NOTICE '===========================================';
END $$;
