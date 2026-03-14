
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const logData = await request.json();
    
    // Log to console for now
    console.log('[Frontend Log]', logData);

    return NextResponse.json({ success: true }, { status: 200 });
  } catch (error) {
    console.error('Error processing log:', error);
    return NextResponse.json({ success: false }, { status: 500 });
  }
}
